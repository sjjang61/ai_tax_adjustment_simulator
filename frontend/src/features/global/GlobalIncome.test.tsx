import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { GlobalIncomeInput } from '../../api/types';
import {
  db,
  fixtureBusinessRecord,
  fixtureGlobalResult,
  fixtureInput,
  makeSimulation,
  storeBusiness,
} from '../../test/handlers';
import { renderWithProviders } from '../../test/render';
import { server } from '../../test/server';
import { GlobalHomePage } from './GlobalHomePage';
import { GlobalIncomePage } from './GlobalIncomePage';

type User = ReturnType<typeof userEvent.setup>;

function renderNew() {
  return renderWithProviders(<></>, {
    route: '/global-income/new',
    routes: [
      { path: '/global-income/new', element: <GlobalIncomePage /> },
      { path: '/global-income/:id', element: <GlobalIncomePage /> },
    ],
  });
}

function captureCalculations(): GlobalIncomeInput[] {
  const bodies: GlobalIncomeInput[] = [];
  server.events.on('request:start', async ({ request }) => {
    if (request.url.endsWith('/global-income/calculate')) {
      bodies.push((await request.clone().json()) as GlobalIncomeInput);
    }
  });
  return bodies;
}

async function typeMoney(user: User, scope: HTMLElement, label: string, value: string) {
  const input = within(scope).getByLabelText(label);
  await user.clear(input);
  await user.type(input, value);
}

describe('종합소득세 시뮬레이터', () => {
  afterEach(() => server.events.removeAllListeners());

  it('연말정산 결과를 불러와 사업·기타소득을 더해 계산하고 저장한다', async () => {
    const user = userEvent.setup();
    const yearEnd = makeSimulation({ name: '2025 연말정산' });
    db.simulations.set(yearEnd.id, yearEnd);
    const bodies = captureCalculations();
    renderNew();

    // 1) 연말정산 결과 불러오기
    const importBox = await screen.findByRole('region', { name: '연말정산 결과 불러오기' });
    await user.selectOptions(
      await within(importBox).findByLabelText('불러올 연말정산 결과'),
      String(yearEnd.id),
    );
    await user.click(within(importBox).getByRole('button', { name: '불러오기' }));
    expect(await within(importBox).findByRole('status')).toHaveTextContent(
      '「2025 연말정산」의 근로소득·공제 입력을 불러왔습니다.',
    );

    // 2) 불러온 근로소득 확인
    await user.click(screen.getByRole('button', { name: '다음' }));
    expect(await screen.findByLabelText('연간 근로소득 (비과세 포함)')).toHaveValue('60,000,000');

    // 3) 사업·기타소득 추가
    await user.click(screen.getByRole('button', { name: /5단계 사업·기타 소득/ }));
    await user.click(await screen.findByRole('button', { name: '+ 사업소득 추가' }));
    const biz = screen.getByText('사업소득 1').closest('.income-item') as HTMLElement;
    await user.type(within(biz).getByLabelText('이름(선택)'), '프리랜서 강의');
    await typeMoney(user, biz, '총수입금액', '2000만');
    const rate = within(biz).getByLabelText('경비율 (%)');
    await user.clear(rate);
    await user.type(rate, '64.1');

    await user.click(screen.getByRole('button', { name: '+ 기타소득 추가' }));
    const other = screen.getByText('기타소득 1').closest('.income-item') as HTMLElement;
    await typeMoney(user, other, '지급받은 금액 (총수입금액)', '200만');
    await user.click(within(other).getByLabelText('원천징수세액 직접 입력'));
    await typeMoney(user, other, '원천징수된 소득세', '16만');

    await waitFor(() => {
      const last = bodies.at(-1);
      expect(last?.other_incomes[0]?.withholding_tax).toBe(160_000);
    });
    const sent = bodies.at(-1) as GlobalIncomeInput;
    expect(sent.base.income.annual_earned_income).toBe(60_000_000);
    expect(sent.business_incomes[0]).toMatchObject({
      name: '프리랜서 강의',
      revenue: 20_000_000,
      expense_method: 'rate',
      expense_rate: '64.1',
      withholding_tax: null,
    });
    expect(sent.other_incomes[0]).toMatchObject({ kind: 'deemed_expense', revenue: 2_000_000 });

    // 4) 결과 (백엔드 계산 결과 표시)
    await user.click(screen.getByRole('button', { name: '다음' }));
    expect(await screen.findByTestId('global-total')).toHaveTextContent(
      `${Math.abs(fixtureGlobalResult.total_balance_due).toLocaleString('ko-KR')}원`,
    );
    const incomes = screen.getByRole('region', { name: '소득별 내역' });
    expect(within(incomes).getByText('프리랜서 강의')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: '기납부세액 내역' })).toHaveTextContent(
      '근로소득 (연말정산 결정세액)',
    );
    expect(screen.getByRole('note')).toHaveTextContent('종합소득세 신고');

    // 5) 저장 → 원본 연말정산 연결
    await user.click(screen.getByRole('button', { name: '저장' }));
    expect(await screen.findByTestId('global-editing-name')).toHaveTextContent('2025 연말정산');
    const saved = [...db.globals.values()];
    expect(saved).toHaveLength(1);
    expect(saved[0]?.source_simulation_id).toBe(yearEnd.id);
  });

  it('불러올 연말정산 결과가 없으면 새로 입력으로 시작한다', async () => {
    const user = userEvent.setup();
    renderNew();
    expect(await screen.findByText(/저장된 연말정산 결과가 없습니다/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '새로 입력하기' }));
    expect(await screen.findByRole('heading', { name: '기본 정보' })).toBeInTheDocument();
    expect(screen.getByLabelText('연간 근로소득 (비과세 포함)')).toHaveValue('');
  });

  it('경비율이 100%를 넘으면 다음 단계로 넘어가지 않는다', async () => {
    const user = userEvent.setup();
    renderNew();
    await user.click(await screen.findByRole('button', { name: /5단계 사업·기타 소득/ }));
    await user.click(await screen.findByRole('button', { name: '+ 사업소득 추가' }));
    const rate = screen.getByLabelText('경비율 (%)');
    await user.clear(rate);
    await user.type(rate, '150');
    await user.click(screen.getByRole('button', { name: '다음' }));
    expect(await screen.findByText('경비율은 100%를 넘을 수 없습니다')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '사업·기타 소득' })).toBeInTheDocument();
  });

  it('공제 단계에서 근로소득자 전용 공제를 안내한다', async () => {
    const user = userEvent.setup();
    renderNew();
    await user.click(await screen.findByRole('button', { name: /4단계 공제/ }));
    expect(await screen.findByText(/근로소득이 있을 때만 적용됩니다/)).toBeInTheDocument();
  });
});

describe('종합소득세 저장 목록', () => {
  it('저장된 시뮬레이션을 보여주고 삭제할 수 있다', async () => {
    const user = userEvent.setup();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    db.globals.set(7, {
      id: 7,
      name: '2025 종소세',
      tax_year: 2025,
      total_balance_due: 480_700,
      source_simulation_id: 1,
      created_at: '2026-05-01T00:00:00Z',
      updated_at: '2026-05-01T00:00:00Z',
      input: {
        tax_year: 2025,
        base: fixtureInput,
        business_incomes: [],
        other_incomes: [],
        other_income_taxation: 'auto',
        interim_prepayment: 0,
        earned_prepaid_tax: null,
      },
      result: fixtureGlobalResult,
    });
    renderWithProviders(<GlobalHomePage />);
    const row = (await screen.findByText('2025 종소세')).closest('li') as HTMLElement;
    expect(within(row).getByText('납부 480,700원')).toBeInTheDocument();
    expect(within(row).getByText(/연말정산 결과 연동/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '새로 계산하기' })).toHaveAttribute(
      'href',
      '/global-income/new',
    );
    await user.click(within(row).getByRole('button', { name: '삭제' }));
    expect(await screen.findByText('저장된 종합소득세 시뮬레이션이 없습니다.')).toBeInTheDocument();
  });
});

describe('종합소득세 입력: 사업자 관리에서 지분만큼 불러오기', () => {
  afterEach(() => server.events.removeAllListeners());

  it('사업자와 본인 대표자를 고르면 지분만큼의 사업소득이 추가된다', async () => {
    const user = userEvent.setup();
    storeBusiness(9, fixtureBusinessRecord);
    const bodies = captureCalculations();
    renderNew();
    await user.click(await screen.findByRole('button', { name: /5단계 사업·기타 소득/ }));
    const panel = await screen.findByRole('region', { name: '사업자 관리에서 불러오기' });
    await user.selectOptions(await within(panel).findByLabelText('사업자 선택'), '9');
    const partner = within(panel).getByLabelText('본인 대표자 선택');
    await waitFor(() => expect(partner).toBeEnabled());
    await user.selectOptions(partner, '0');
    await user.click(within(panel).getByRole('button', { name: '지분만큼 불러오기' }));
    expect(within(panel).getByRole('status')).toHaveTextContent('김대표 지분(60%)');

    const biz = screen.getByText('사업소득 1').closest('.income-item') as HTMLElement;
    expect(within(biz).getByLabelText('이름(선택)')).toHaveValue('공동 스튜디오 (지분 60%)');
    expect(within(biz).getByLabelText('총수입금액')).toHaveValue('60,000,000');
    expect(within(biz).getByLabelText('필요경비')).toHaveValue('24,000,000');
    await waitFor(() =>
      expect(bodies.at(-1)?.business_incomes[0]).toMatchObject({
        revenue: 60_000_000,
        expense_method: 'book',
        expenses: 24_000_000,
        withholding_tax: 1_800_000,
      }),
    );
  });
});
