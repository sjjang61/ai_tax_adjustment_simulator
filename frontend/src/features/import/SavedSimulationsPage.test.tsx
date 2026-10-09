import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import type { SimulationExport } from '../../api/types';
import { BASE, db, fixtureInput, makeSimulation } from '../../test/handlers';
import { renderWithProviders } from '../../test/render';
import { server } from '../../test/server';
import { SimulationPage } from '../simulation/SimulationPage';
import { SavedSimulationsPage } from './SavedSimulationsPage';

function renderSaved() {
  return renderWithProviders(<></>, {
    route: '/saved',
    routes: [
      { path: '/saved', element: <SavedSimulationsPage /> },
      { path: '/simulations/:id', element: <SimulationPage /> },
    ],
  });
}

function seed(name = '2025 연말정산') {
  const sim = makeSimulation({ name });
  db.simulations.set(sim.id, sim);
  return sim;
}

describe('SavedSimulationsPage', () => {
  it('저장된 시뮬레이션이 없으면 안내한다', async () => {
    renderSaved();
    expect(await screen.findByText('저장된 시뮬레이션이 없습니다.')).toBeInTheDocument();
  });

  it('작년 시뮬레이션을 올해로 이월하고 이월 경고를 보여준다', async () => {
    const user = userEvent.setup();
    const sim = seed();
    let requestUrl = '';
    server.events.on('request:start', ({ request }) => {
      if (request.url.includes('carry-over')) requestUrl = request.url;
    });
    renderSaved();
    const item = (await screen.findByText(sim.name)).closest('li') as HTMLElement;
    expect(within(item).getByText('2025년 귀속')).toBeInTheDocument();
    expect(within(item).getByText(/환급/)).toBeInTheDocument();

    await user.click(within(item).getByRole('button', { name: '올해로 이월' }));
    const form = within(item).getByRole('form', { name: '올해로 이월' });
    expect(within(form).getByRole('combobox')).toHaveValue('2026');
    await user.type(within(form).getByPlaceholderText('예: 3.5'), '3.5');
    await user.click(within(form).getByRole('button', { name: '초안 만들기' }));

    expect(await screen.findByText('작년 데이터 이월 결과 확인')).toBeInTheDocument();
    expect(screen.getByText(/70세가 되어 경로우대/)).toBeInTheDocument();
    expect(new URL(requestUrl).searchParams.get('target_year')).toBe('2026');
    expect(new URL(requestUrl).searchParams.get('salary_increase_rate')).toBe('3.5');
    expect(await screen.findByTestId('editing-name')).toHaveTextContent(
      `${sim.name} → 2026년 초안`,
    );
    server.events.removeAllListeners();
  });

  it('잘못된 인상률은 막는다', async () => {
    const user = userEvent.setup();
    seed();
    renderSaved();
    await user.click(await screen.findByRole('button', { name: '올해로 이월' }));
    await user.type(screen.getByPlaceholderText('예: 3.5'), '200');
    expect(screen.getByText('인상률은 -50% ~ 100% 사이로 입력하세요')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '초안 만들기' })).toBeDisabled();
  });

  it('JSON으로 내보낸다', async () => {
    const user = userEvent.setup();
    seed();
    const createObjectURL = vi.fn(() => 'blob:x');
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    renderSaved();
    await user.click(await screen.findByRole('button', { name: '내보내기' }));
    await waitFor(() => expect(click).toHaveBeenCalled());
    expect(createObjectURL).toHaveBeenCalled();
    click.mockRestore();
  });

  it('삭제 확인 후 목록에서 제거한다', async () => {
    const user = userEvent.setup();
    const sim = seed();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderSaved();
    await user.click(await screen.findByRole('button', { name: '삭제' }));
    expect(await screen.findByText('저장된 시뮬레이션이 없습니다.')).toBeInTheDocument();
    expect(db.simulations.has(sim.id)).toBe(false);
  });

  it('JSON 파일을 가져와 올해 초안으로 변환한다', async () => {
    const user = userEvent.setup();
    let target: string | null = null;
    server.use(
      http.post(`${BASE}/simulations/import`, async ({ request }) => {
        target = new URL(request.url).searchParams.get('target_year');
        const doc = (await request.json()) as SimulationExport;
        const sim = makeSimulation({ name: doc.name, input: { ...fixtureInput, tax_year: 2026 } });
        db.simulations.set(sim.id, sim);
        return HttpResponse.json({ simulation: sim, warnings: [] }, { status: 201 });
      }),
    );
    renderSaved();
    const doc: SimulationExport = {
      schema_version: 1,
      tax_year: 2025,
      name: '가져온 시뮬레이션',
      input: fixtureInput as unknown as SimulationExport['input'],
    };
    const file = new File([JSON.stringify(doc)], 'sim.json', { type: 'application/json' });
    const panel = screen.getByRole('region', { name: 'JSON 파일 가져오기' });
    await user.upload(within(panel).getByLabelText('파일'), file);
    await user.selectOptions(within(panel).getByLabelText('변환할 귀속연도'), '2026');
    await user.click(within(panel).getByRole('button', { name: '가져오기' }));
    expect(await screen.findByTestId('editing-name')).toHaveTextContent('가져온 시뮬레이션');
    expect(target).toBe('2026');
  });

  it('파일 없이 가져오기를 누르면 안내하고, 서버 오류를 표시한다', async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${BASE}/simulations/import`, () =>
        HttpResponse.json(
          { code: 'unsupported_schema_version', message: '지원하지 않는 스키마', details: null },
          { status: 400 },
        ),
      ),
    );
    renderSaved();
    const panel = screen.getByRole('region', { name: 'JSON 파일 가져오기' });
    await user.click(within(panel).getByRole('button', { name: '가져오기' }));
    expect(within(panel).getByText('파일을 선택하세요.')).toBeInTheDocument();

    const file = new File(['{"schema_version": 99}'], 'bad.json', { type: 'application/json' });
    await user.upload(within(panel).getByLabelText('파일'), file);
    await user.click(within(panel).getByRole('button', { name: '가져오기' }));
    expect(await within(panel).findByText(/지원하지 않는 스키마/)).toBeInTheDocument();
  });
});
