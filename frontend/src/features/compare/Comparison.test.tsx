import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { SimulationComparison } from '../../api/types';
import { db, fixtureComparison, fixtureInput, makeSimulation } from '../../test/handlers';
import { renderWithProviders } from '../../test/render';
import { SavedSimulationsPage } from '../import/SavedSimulationsPage';
import { SimulationPage } from '../simulation/SimulationPage';
import { ComparePage } from './ComparePage';
import { ComparisonView } from './ComparisonView';

function seed(name: string, input = fixtureInput) {
  const sim = makeSimulation({ name, input });
  db.simulations.set(sim.id, sim);
  return sim;
}

function renderSaved(id: number) {
  return renderWithProviders(<></>, {
    route: `/simulations/${id}`,
    routes: [{ path: '/simulations/:id', element: <SimulationPage /> }],
  });
}

const BASE_COMPARISON: SimulationComparison = {
  base: {
    id: 1,
    name: '기준',
    tax_year: 2025,
    schema_version: 1,
    determined_tax: 0,
    total_balance_due: 0,
    source_simulation_id: null,
    created_at: '2026-01-10T00:00:00Z',
    updated_at: '2026-01-10T00:00:00Z',
  },
  snapshot_differs: false,
  comparison: fixtureComparison,
};

describe('ComparisonView', () => {
  it('유리·불리 요약, 지표, 바뀐 입력과 공제를 보여준다', () => {
    render(<ComparisonView data={BASE_COMPARISON} />);
    expect(screen.getByTestId('compare-saving')).toHaveTextContent('396,000원 유리');
    const metrics = screen.getByRole('region', { name: '주요 지표 비교' });
    const determined = within(metrics).getByText('결정세액').closest('tr') as HTMLElement;
    expect(within(determined).getByText('−360,000원')).toBeInTheDocument();
    const inputs = screen.getByRole('region', { name: '바뀐 입력' });
    expect(within(inputs).getByText('퇴직연금(IRP)')).toBeInTheDocument();
    expect(within(inputs).getByText('3,000,000원')).toBeInTheDocument();
    const credits = screen.getByRole('region', { name: '바뀐 세액공제' });
    expect(within(credits).getByText('연금계좌세액공제')).toBeInTheDocument();
    expect(screen.getByRole('note')).toHaveTextContent('국세청 홈택스');
  });

  it('불리·규칙 변경·연도 변경을 안내한다', () => {
    render(
      <ComparisonView
        data={{
          ...BASE_COMPARISON,
          snapshot_differs: true,
          comparison: { ...fixtureComparison, saving: -1000, tax_year_changed: true },
        }}
      />,
    );
    expect(screen.getByTestId('compare-saving')).toHaveTextContent('1,000원 불리');
    expect(screen.getByText(/저장 당시 결과와 현재 규칙으로/)).toBeInTheDocument();
    expect(screen.getByText(/귀속연도가 다릅니다/)).toBeInTheDocument();
  });
});

describe('저장본과 비교 (위저드)', () => {
  it('저장된 시뮬레이션을 수정하면 미리보기와 결과 탭에 저장본 대비 차이를 보여준다', async () => {
    const user = userEvent.setup();
    const sim = seed('2025 기본');
    renderSaved(sim.id);
    const preview = await screen.findByRole('complementary', { name: '실시간 미리보기' });
    expect(await within(preview).findByTestId('preview-compare')).toHaveTextContent(
      '저장본과 같음',
    );

    for (let i = 0; i < 3; i++) await user.click(screen.getByRole('button', { name: '다음' }));
    expect(await screen.findByRole('heading', { name: '세액공제' })).toBeInTheDocument();
    await user.type(screen.getByLabelText('퇴직연금(IRP) 납입액'), '300만');
    expect(await within(preview).findByText(/저장본 대비 396,000원 유리/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '다음' }));
    await user.click(await screen.findByRole('tab', { name: /저장본과 비교 \(1개 변경\)/ }));
    expect(await screen.findByTestId('compare-saving')).toHaveTextContent('396,000원 유리');
    await user.click(screen.getByRole('tab', { name: '현재 결과' }));
    expect(screen.getByRole('region', { name: '단계별 계산 내역' })).toBeInTheDocument();
  });

  it('새 항목으로 저장하면 원본은 그대로 두고 새 시뮬레이션을 만든다', async () => {
    const user = userEvent.setup();
    const sim = seed('원본');
    renderSaved(sim.id);
    await user.click(await screen.findByRole('button', { name: '5단계 결과' }));
    const name = await screen.findByLabelText('시뮬레이션 이름');
    await user.clear(name);
    await user.type(name, '변경안');
    await user.click(screen.getByRole('button', { name: '새 항목으로 저장' }));
    expect(await screen.findByTestId('editing-name')).toHaveTextContent('변경안');
    const names = [...db.simulations.values()].map((s) => s.name).sort();
    expect(names).toEqual(['변경안', '원본']);
  });

  it('새 시뮬레이션에는 비교 탭이 없다', async () => {
    const user = userEvent.setup();
    renderWithProviders(<></>, { routes: [{ path: '/', element: <SimulationPage /> }] });
    for (let i = 0; i < 4; i++)
      await user.click(await screen.findByRole('button', { name: '다음' }));
    expect(await screen.findByRole('heading', { name: '결과' })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /저장본과 비교/ })).toBeNull();
  });
});

describe('저장 목록에서 2건 비교', () => {
  it('두 건을 선택해 비교 화면으로 이동한다', async () => {
    const user = userEvent.setup();
    const a = seed('2025 기본');
    const b = seed('IRP 추가안', {
      ...fixtureInput,
      credits: { ...fixtureInput.credits, irp: 3_000_000 },
    });
    renderWithProviders(<></>, {
      route: '/saved',
      routes: [
        { path: '/saved', element: <SavedSimulationsPage /> },
        { path: '/compare/:baseId/:targetId', element: <ComparePage /> },
      ],
    });
    const compareButton = await screen.findByRole('button', { name: '선택한 2건 비교' });
    expect(compareButton).toBeDisabled();
    await user.click(await screen.findByLabelText(`${a.name} 비교 선택`));
    await user.click(screen.getByLabelText(`${b.name} 비교 선택`));
    expect(compareButton).toBeEnabled();
    await user.click(compareButton);
    expect(
      await screen.findByRole('heading', { name: '비교: 2025 기본 → IRP 추가안' }),
    ).toBeInTheDocument();
    expect(await screen.findByTestId('compare-saving')).toHaveTextContent('396,000원 유리');
  });
});
