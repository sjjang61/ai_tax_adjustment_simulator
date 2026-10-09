import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { BusinessRecord } from '../../api/types';
import {
  db,
  fixtureBusinessRecord,
  fixturePartnership,
  makeSimulation,
  storeBusiness,
} from '../../test/handlers';
import { renderWithProviders } from '../../test/render';
import { server } from '../../test/server';
import { BusinessFormPage } from './BusinessFormPage';
import { BusinessListPage } from './BusinessListPage';
import { PartnershipPage } from './PartnershipPage';

function renderBusiness(route: string) {
  return renderWithProviders(<></>, {
    route,
    routes: [
      { path: '/global-income/businesses', element: <BusinessListPage /> },
      { path: '/global-income/businesses/new', element: <BusinessFormPage /> },
      { path: '/global-income/businesses/:id', element: <BusinessFormPage /> },
      { path: '/global-income/businesses/:id/partnership', element: <PartnershipPage /> },
    ],
  });
}

describe('사업자 소득관리', () => {
  afterEach(() => server.events.removeAllListeners());

  it('공동대표 지분(6:4)과 연말정산 연결을 입력하면 배분 미리보기를 보여주고 저장한다', async () => {
    const user = userEvent.setup();
    const kim = makeSimulation({ name: '김대표 연말정산' });
    db.simulations.set(kim.id, kim);
    const saved: BusinessRecord[] = [];
    server.events.on('request:start', async ({ request }) => {
      if (request.method === 'POST' && request.url.endsWith('/businesses')) {
        saved.push(((await request.clone().json()) as { record: BusinessRecord }).record);
      }
    });
    renderBusiness('/global-income/businesses/new');

    await user.type(await screen.findByLabelText('사업장 이름'), '공동 스튜디오');
    const revenue = screen.getByLabelText('총수입금액 (사업장 전체)');
    await user.type(revenue, '1억');
    const expenses = screen.getByLabelText('필요경비 (사업장 전체)');
    await user.type(expenses, '4000만');

    await user.type(screen.getByLabelText('대표자 1'), '김대표');
    const share1 = screen.getAllByLabelText('지분')[0] as HTMLElement;
    await user.clear(share1);
    await user.type(share1, '6');
    await user.selectOptions(
      screen.getAllByLabelText('연말정산 결과 연결')[0] as HTMLElement,
      String(kim.id),
    );
    await user.type(screen.getByLabelText('대표자 2'), '이대표');
    const share2 = screen.getAllByLabelText('지분')[1] as HTMLElement;
    await user.clear(share2);
    await user.type(share2, '4');

    const preview = await screen.findByRole('region', { name: '지분별 배분' });
    expect(within(preview).getByText('60%')).toBeInTheDocument();
    expect(within(preview).getByText('36,000,000원')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '저장' }));
    expect(
      await screen.findByRole('link', { name: '공동대표 일괄 종합소득세 계산' }),
    ).toBeInTheDocument();
    expect(saved[0]).toMatchObject({
      name: '공동 스튜디오',
      revenue: 100_000_000,
      expense_method: 'book',
      expenses: 40_000_000,
      partners: [
        { name: '김대표', share: 6, simulation_id: kim.id },
        { name: '이대표', share: 4, simulation_id: null },
      ],
    });
  });

  it('같은 연말정산 결과를 두 대표에 연결하면 저장하지 않는다', async () => {
    const user = userEvent.setup();
    const kim = makeSimulation({ name: '김대표 연말정산' });
    db.simulations.set(kim.id, kim);
    renderBusiness('/global-income/businesses/new');
    await user.type(await screen.findByLabelText('사업장 이름'), '스튜디오');
    await user.type(screen.getByLabelText('대표자 1'), 'A');
    await user.type(screen.getByLabelText('대표자 2'), 'B');
    for (const select of screen.getAllByLabelText('연말정산 결과 연결')) {
      await user.selectOptions(select, String(kim.id));
    }
    await user.click(screen.getByRole('button', { name: '저장' }));
    expect(
      await screen.findByText('같은 연말정산 결과를 여러 대표에 연결할 수 없습니다'),
    ).toBeInTheDocument();
    expect(db.businesses.size).toBe(0);
  });

  it('목록에서 공동대표 사업자를 보여준다', async () => {
    storeBusiness(5, fixtureBusinessRecord);
    renderBusiness('/global-income/businesses');
    const row = (await screen.findByText('공동 스튜디오')).closest('li') as HTMLElement;
    expect(within(row).getByText('공동대표 2인')).toBeInTheDocument();
    expect(within(row).getByRole('link', { name: '공동대표 일괄 계산' })).toHaveAttribute(
      'href',
      '/global-income/businesses/5/partnership',
    );
  });

  it('공동대표 일괄 계산: 대표별 결과와 합계를 보여주고 각각 저장한다', async () => {
    const user = userEvent.setup();
    storeBusiness(5, fixtureBusinessRecord);
    renderBusiness('/global-income/businesses/5/partnership');

    const total = await screen.findByTestId('partnership-total');
    expect(total).toHaveTextContent(
      fixturePartnership.combined_total_balance_due.toLocaleString('ko-KR'),
    );
    const kim = screen.getByRole('article', { name: '김대표 결과' });
    expect(within(kim).getByText('지분 60%')).toBeInTheDocument();
    expect(within(kim).getByText('김대표 연말정산')).toBeInTheDocument();
    const lee = screen.getByRole('article', { name: '이대표 결과' });
    expect(within(lee).getByText('연결 안 됨')).toBeInTheDocument();
    expect(within(lee).getByText(/근로소득 없이 계산/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '대표별 종합소득세로 각각 저장' }));
    expect(await screen.findByRole('status')).toHaveTextContent('2건 저장되었습니다');
    const names = [...db.globals.values()].map((g) => g.name);
    expect(names).toEqual([
      '2025년 종합소득세 - 김대표 (공동 스튜디오)',
      '2025년 종합소득세 - 이대표 (공동 스튜디오)',
    ]);
    await waitFor(() =>
      expect([...db.globals.values()][0]?.source_simulation_id).toBe(
        fixturePartnership.partners[0]?.partner.simulation_id,
      ),
    );
  });
});
