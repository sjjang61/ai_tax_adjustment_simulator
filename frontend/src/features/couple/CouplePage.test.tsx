import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { CoupleInput, SimulationInput } from '../../api/types';
import { db, fixtureInput, makeSimulation } from '../../test/handlers';
import { renderWithProviders } from '../../test/render';
import { server } from '../../test/server';
import { CouplePage } from './CouplePage';

type User = ReturnType<typeof userEvent.setup>;

function renderCouple() {
  return renderWithProviders(<></>, {
    route: '/couple',
    routes: [{ path: '/couple', element: <CouplePage /> }],
  });
}

async function next(user: User, name = '다음') {
  await user.click(screen.getByRole('button', { name }));
}

async function typeMoney(
  user: User,
  label: string,
  value: string,
  scope: HTMLElement = document.body,
) {
  const input = within(scope).getByLabelText(label);
  await user.clear(input);
  await user.type(input, value);
}

async function fillUntilShared(user: User) {
  expect(await screen.findByRole('heading', { name: '귀속연도' })).toBeInTheDocument();
  await next(user);
  expect(await screen.findByRole('heading', { name: '본인 정보' })).toBeInTheDocument();
  expect(screen.queryByLabelText('귀속연도')).not.toBeVisible();
  await typeMoney(user, '연간 근로소득 (비과세 포함)', '8000만');
  await next(user);
  expect(await screen.findByRole('heading', { name: '본인 공제' })).toBeInTheDocument();
  expect(screen.getByText(/부양가족 배분」 단계에서 가족별로 입력/)).toBeInTheDocument();
  await next(user);
  expect(await screen.findByRole('heading', { name: '배우자 정보' })).toBeInTheDocument();
  await typeMoney(user, '연간 근로소득 (비과세 포함)', '4000만');
  await next(user);
  await next(user);
  expect(await screen.findByRole('heading', { name: '부양가족 배분' })).toBeInTheDocument();
}

async function addDependent(
  user: User,
  index: number,
  name: string,
  relation: string,
  birth: string,
) {
  await user.click(screen.getByRole('button', { name: '+ 부양가족 추가' }));
  const card = screen.getByText(`부양가족 ${index + 1}`).closest('fieldset') as HTMLElement;
  await user.type(within(card).getByLabelText('이름(선택)'), name);
  await user.selectOptions(within(card).getByLabelText('관계'), relation);
  const birthInput = within(card).getByLabelText('출생연도');
  await user.clear(birthInput);
  await user.type(birthInput, birth);
  return card;
}

describe('CouplePage', () => {
  it('부부 정보와 공유 부양가족을 입력하면 최적 배분과 AI 설명을 보여주고 각자 저장한다', async () => {
    const user = userEvent.setup();
    const bodies: CoupleInput[] = [];
    server.events.on('request:start', async ({ request }) => {
      if (request.url.endsWith('/couples/optimize')) {
        bodies.push((await request.clone().json()) as CoupleInput);
      }
    });
    renderCouple();
    await fillUntilShared(user);

    const mother = await addDependent(user, 0, '어머니', 'lineal_ascendant', '1966');
    await typeMoney(user, '이 가족의 의료비', '300만', mother);
    const child = await addDependent(user, 1, '첫째', 'lineal_descendant', '2012');
    await user.selectOptions(within(child).getByLabelText('교육비 구분'), 'school');
    await typeMoney(user, '이 가족의 교육비', '200만', child);
    expect(within(mother).getByText(/65세 이상·6세 이하/)).toBeInTheDocument();

    await next(user, '최적 배분 계산');
    expect(await screen.findByTestId('couple-saving')).toHaveTextContent('55,000원 절세');
    const sent = bodies.at(-1) as CoupleInput;
    expect(sent.tax_year).toBe(2025);
    expect(sent.primary.income.annual_earned_income).toBe(80_000_000);
    expect(sent.spouse.income.annual_earned_income).toBe(40_000_000);
    expect(sent.primary.taxpayer.is_married && sent.spouse.taxpayer.is_married).toBe(true);
    expect(
      sent.shared_dependents.map((d) => [d.name, d.medical_expense, d.education_amount]),
    ).toEqual([
      ['어머니', 3_000_000, 0],
      ['첫째', 0, 2_000_000],
    ]);

    const allocation = screen.getByRole('region', { name: '부양가족 배분' });
    const motherRow = within(allocation).getByText('어머니').closest('tr') as HTMLElement;
    expect(within(motherRow).getByText('배우자')).toBeInTheDocument();
    expect(within(motherRow).getByText('변경')).toBeInTheDocument();

    // 추천 배분 적용 → 다음 계산 요청에 반영
    await user.click(screen.getByRole('button', { name: '추천 배분을 현재 배분으로 적용' }));
    await waitFor(() => expect(bodies.at(-1)?.shared_dependents[0]?.assigned_to).toBe('spouse'));

    // AI 설명 (우측 패널)
    const panel = screen.getByRole('complementary', { name: 'AI 배분 설명' });
    await user.click(within(panel).getByRole('button', { name: 'AI 설명 받기' }));
    expect(await within(panel).findByText('의료비 공제 문턱이 낮습니다.')).toBeInTheDocument();
    expect(within(panel).getByText(/총급여 25% 문턱/)).toBeInTheDocument();

    // 각자 저장
    await user.click(screen.getByRole('button', { name: '추천 배분으로 각자 저장' }));
    expect(await screen.findByRole('status')).toHaveTextContent('저장되었습니다');
    const saved = [...db.simulations.values()];
    expect(saved.map((s) => s.name)).toEqual(['2025년 맞벌이 - 본인', '2025년 맞벌이 - 배우자']);
    expect((saved[1]?.input as SimulationInput).dependents.map((d) => d.name)).toEqual(['어머니']);
    server.events.removeAllListeners();
  });

  it('배우자 정보 오류가 있으면 다음 단계로 넘어가지 않는다', async () => {
    const user = userEvent.setup();
    renderCouple();
    await next(user);
    await next(user);
    await next(user);
    expect(await screen.findByRole('heading', { name: '배우자 정보' })).toBeInTheDocument();
    await typeMoney(user, '연간 근로소득 (비과세 포함)', '1000만');
    await typeMoney(user, '비과세소득', '2000만');
    await next(user);
    expect(
      await screen.findByText('비과세소득은 연간 근로소득을 초과할 수 없습니다'),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '배우자 정보' })).toBeInTheDocument();
  });

  it('공유 부양가족 출생연도를 비우면 계산 단계로 넘어가지 않는다', async () => {
    const user = userEvent.setup();
    renderCouple();
    await fillUntilShared(user);
    await user.click(screen.getByRole('button', { name: '+ 부양가족 추가' }));
    await user.clear(screen.getByLabelText('출생연도'));
    await next(user, '최적 배분 계산');
    expect(await screen.findByText('출생연도를 입력하세요')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '부양가족 배분' })).toBeInTheDocument();
  });

  it('상단 단계를 눌러 배우자 공제·부양가족 배분 단계로 바로 이동한다', async () => {
    const user = userEvent.setup();
    renderCouple();
    await user.click(await screen.findByRole('button', { name: '6단계 부양가족 배분' }));
    expect(await screen.findByRole('heading', { name: '부양가족 배분' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '5단계 배우자 공제 (완료)' }));
    expect(await screen.findByRole('heading', { name: '배우자 공제' })).toBeInTheDocument();
    expect(screen.getByText('5 / 7 단계')).toBeInTheDocument();
  });

  it('저장된 개인 시뮬레이션을 본인·배우자 정보로 불러오고 부양가족은 배분 단계로 옮긴다', async () => {
    const user = userEvent.setup();
    const child = {
      name: '첫째',
      relation: 'lineal_descendant' as const,
      birth_year: 2015,
      disabled: false,
      income_amount: 0,
      income_is_salary_only: false,
      born_or_adopted_this_year: false,
      child_order: null,
    };
    const husband = makeSimulation({
      name: '남편 2025',
      input: {
        ...fixtureInput,
        income: { annual_earned_income: 80_000_000, non_taxable_income: 0 },
        dependents: [child],
        credits: {
          ...fixtureInput.credits,
          education: [{ kind: 'school', amount: 2_000_000, label: '첫째' }],
        },
      },
    });
    const wife = makeSimulation({
      name: '아내 2025',
      input: {
        ...fixtureInput,
        income: { annual_earned_income: 40_000_000, non_taxable_income: 0 },
        dependents: [child],
      },
    });
    db.simulations.set(husband.id, husband);
    db.simulations.set(wife.id, wife);
    const bodies: CoupleInput[] = [];
    server.events.on('request:start', async ({ request }) => {
      if (request.url.endsWith('/couples/optimize')) {
        bodies.push((await request.clone().json()) as CoupleInput);
      }
    });

    renderCouple();
    await next(user);
    const primaryPanel = await screen.findByRole('region', { name: '본인 정보 불러오기' });
    await user.selectOptions(
      within(primaryPanel).getByLabelText('본인으로 불러올 시뮬레이션'),
      String(husband.id),
    );
    await user.click(within(primaryPanel).getByRole('button', { name: '본인 정보로 불러오기' }));
    expect(await within(primaryPanel).findByRole('status')).toHaveTextContent(
      '부양가족 1명을 「부양가족 배분」 단계로 옮겼습니다 (현재 공제: 본인).',
    );
    expect(screen.getByLabelText('연간 근로소득 (비과세 포함)')).toHaveValue('80,000,000');

    await user.click(screen.getByRole('button', { name: /4단계 배우자 정보/ }));
    const spousePanel = await screen.findByRole('region', { name: '배우자 정보 불러오기' });
    await user.selectOptions(
      within(spousePanel).getByLabelText('배우자로 불러올 시뮬레이션'),
      String(wife.id),
    );
    await user.click(within(spousePanel).getByRole('button', { name: '배우자 정보로 불러오기' }));
    expect(await within(spousePanel).findByRole('status')).toHaveTextContent(
      '첫째는 이미 「부양가족 배분」에 있어 추가하지 않았습니다.',
    );
    expect(screen.getByLabelText('연간 근로소득 (비과세 포함)')).toHaveValue('40,000,000');

    await user.click(screen.getByRole('button', { name: /6단계 부양가족 배분/ }));
    expect(await screen.findByText('부양가족 1')).toBeInTheDocument();
    expect(screen.queryByText('부양가족 2')).toBeNull();
    expect(screen.getByLabelText('이름(선택)')).toHaveValue('첫째');
    expect(screen.getByLabelText('교육비 구분')).toHaveValue('school');

    await next(user, '최적 배분 계산');
    await screen.findByTestId('couple-saving');
    const sent = bodies.at(-1) as CoupleInput;
    expect(sent.primary.income.annual_earned_income).toBe(80_000_000);
    expect(sent.spouse.income.annual_earned_income).toBe(40_000_000);
    expect(sent.primary.dependents).toEqual([]);
    expect(sent.primary.credits.education).toEqual([]);
    expect(sent.shared_dependents).toHaveLength(1);
    expect(sent.shared_dependents[0]).toMatchObject({
      name: '첫째',
      assigned_to: 'primary',
      education_kind: 'school',
      education_amount: 2_000_000,
    });
    server.events.removeAllListeners();
  });
});
