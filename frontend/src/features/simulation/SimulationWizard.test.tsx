import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import type { SimulationInput } from '../../api/types';
import { BASE, db } from '../../test/handlers';
import { renderWithProviders } from '../../test/render';
import { server } from '../../test/server';
import { SimulationPage } from './SimulationPage';

function renderNew() {
  return renderWithProviders(<></>, {
    routes: [
      { path: '/', element: <SimulationPage /> },
      { path: '/simulations/:id', element: <SimulationPage /> },
    ],
  });
}

async function fillSalary(user: ReturnType<typeof userEvent.setup>, value: string) {
  const input = await screen.findByLabelText('연간 근로소득 (비과세 포함)');
  await user.clear(input);
  await user.type(input, value);
}

describe('SimulationWizard', () => {
  it('단계를 이동하고 결과 화면에 백엔드 계산 결과를 표시한다', async () => {
    const user = userEvent.setup();
    renderNew();
    expect(await screen.findByRole('heading', { name: '기본 정보' })).toBeInTheDocument();
    await fillSalary(user, '6000만');

    await user.click(screen.getByRole('button', { name: '다음' }));
    expect(await screen.findByRole('heading', { name: '인적공제' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '다음' }));
    expect(await screen.findByRole('heading', { name: '소득공제' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '다음' }));
    expect(await screen.findByRole('heading', { name: '세액공제' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '다음' }));
    expect(await screen.findByRole('heading', { name: '결과' })).toBeInTheDocument();
    expect(await screen.findByText('예상 환급액')).toBeInTheDocument();
    expect(screen.getByRole('note')).toHaveTextContent('국세청 홈택스');

    await user.click(screen.getByRole('button', { name: '이전' }));
    expect(screen.getByRole('heading', { name: '세액공제' })).toBeInTheDocument();
  });

  it('입력 검증 오류가 있으면 다음 단계로 넘어가지 않는다', async () => {
    const user = userEvent.setup();
    renderNew();
    await fillSalary(user, '1000만');
    const nonTaxable = screen.getByLabelText('비과세소득');
    await user.type(nonTaxable, '2000만');
    await user.click(screen.getByRole('button', { name: '다음' }));
    expect(
      await screen.findByText('비과세소득은 연간 근로소득을 초과할 수 없습니다'),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '기본 정보' })).toBeInTheDocument();
  });

  it('출생연도를 비우면 오류를 표시한다', async () => {
    const user = userEvent.setup();
    renderNew();
    const birth = await screen.findByLabelText('출생연도');
    await user.clear(birth);
    await user.click(screen.getByRole('button', { name: '다음' }));
    expect(await screen.findByText('출생연도를 입력하세요')).toBeInTheDocument();
  });

  it('입력 변경 시 실시간 미리보기를 요청한다', async () => {
    const user = userEvent.setup();
    const bodies: SimulationInput[] = [];
    server.use(
      http.post(`${BASE}/simulations/calculate`, async ({ request }) => {
        bodies.push((await request.json()) as SimulationInput);
        return HttpResponse.json(
          { code: 'x', message: '계산 서버 오류', details: null },
          { status: 500 },
        );
      }),
    );
    renderNew();
    await fillSalary(user, '5000만');
    await waitFor(() =>
      expect(bodies.some((b) => b.income.annual_earned_income === 50_000_000)).toBe(true),
    );
    const preview = screen.getByRole('complementary', { name: '실시간 미리보기' });
    expect(await within(preview).findByRole('alert')).toHaveTextContent('계산 서버 오류');
  });

  it('부양가족을 추가·삭제할 수 있다', async () => {
    const user = userEvent.setup();
    renderNew();
    await fillSalary(user, '5000만');
    await user.click(screen.getByRole('button', { name: '다음' }));
    expect(await screen.findByText('등록된 부양가족이 없습니다.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '+ 부양가족 추가' }));
    expect(screen.getByText('부양가족 1')).toBeInTheDocument();
    await user.click(screen.getByLabelText('올해 출생·입양'));
    expect(screen.getByLabelText('몇째 자녀인가요?')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '부양가족 1 삭제' }));
    expect(screen.getByText('등록된 부양가족이 없습니다.')).toBeInTheDocument();
  });

  it('저장은 결과 단계에서 하고, 저장 후에도 같은 단계를 유지한다', async () => {
    const user = userEvent.setup();
    renderNew();
    await fillSalary(user, '5000만');
    expect(screen.queryByLabelText('시뮬레이션 이름')).toBeNull(); // 입력 단계에는 저장 패널 없음
    await user.click(screen.getByRole('button', { name: '5단계 결과' }));
    const name = await screen.findByLabelText('시뮬레이션 이름');
    await user.clear(name);
    await user.type(name, '내 2025 연말정산');
    await user.click(screen.getByRole('button', { name: '저장' }));
    expect(await screen.findByRole('button', { name: '변경 저장' })).toBeInTheDocument();
    const saved = [...db.simulations.values()];
    expect(saved).toHaveLength(1);
    expect(saved[0]?.name).toBe('내 2025 연말정산');
    expect(saved[0]?.input.income.annual_earned_income).toBe(50_000_000);
    expect(screen.getByRole('heading', { name: '결과' })).toBeInTheDocument();
    expect(screen.getByTestId('editing-name')).toHaveTextContent('내 2025 연말정산');
  });

  it('결과 화면 우측에 AI 추천을 보여주고, 적용하면 폼 값이 바뀌어 다시 계산한다', async () => {
    const user = userEvent.setup();
    const bodies: SimulationInput[] = [];
    server.events.on('request:start', async ({ request }) => {
      if (request.url.endsWith('/simulations/calculate')) {
        bodies.push((await request.clone().json()) as SimulationInput);
      }
    });
    renderNew();
    await fillSalary(user, '6000만');
    for (let i = 0; i < 4; i++) await user.click(screen.getByRole('button', { name: '다음' }));
    const panel = await screen.findByRole('complementary', { name: 'AI 추천' });
    expect(screen.queryByRole('complementary', { name: '실시간 미리보기' })).toBeNull();

    await waitFor(() =>
      expect(within(panel).getByRole('button', { name: 'AI 추천 받기' })).toBeEnabled(),
    );
    await user.click(within(panel).getByRole('button', { name: 'AI 추천 받기' }));
    await user.click(await within(panel).findByRole('button', { name: '적용해 보기' }));
    await waitFor(() => expect(bodies.some((b) => b.credits.irp === 3_000_000)).toBe(true));
    server.events.removeAllListeners();
  });

  it('국민성장펀드 입력은 2026년 귀속에서만 보인다', async () => {
    const user = userEvent.setup();
    renderNew();
    await fillSalary(user, '6000만');
    await user.click(screen.getByRole('button', { name: '다음' }));
    await user.click(screen.getByRole('button', { name: '다음' }));
    expect(await screen.findByRole('heading', { name: '소득공제' })).toBeInTheDocument();
    expect(screen.queryByLabelText('국민성장펀드 납입액')).toBeNull();

    await user.click(screen.getByRole('button', { name: /기본 정보/ }));
    await user.selectOptions(await screen.findByLabelText('귀속연도'), '2026');
    await user.click(screen.getByRole('button', { name: '다음' }));
    await user.click(screen.getByRole('button', { name: '다음' }));
    const field = await screen.findByLabelText('국민성장펀드 납입액');
    expect(
      screen.getByText(/30,000,000원 이하 40%, 50,000,000원 이하 20%, 70,000,000원 이하 10%/),
    ).toBeInTheDocument();
    expect(screen.getByText(/최대 18,000,000원/)).toBeInTheDocument();
    await user.type(field, '3000만');
    await user.tab();
    expect(field).toHaveValue('30,000,000');
  });

  it('상단 단계를 눌러 이후 단계로 바로 이동하고 다시 돌아올 수 있다', async () => {
    const user = userEvent.setup();
    renderNew();
    await fillSalary(user, '5000만');
    await user.click(screen.getByRole('button', { name: '4단계 세액공제' }));
    expect(await screen.findByRole('heading', { name: '세액공제' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '1단계 기본 정보 (완료)' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '5단계 결과' }));
    expect(await screen.findByText('예상 환급액')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '1단계 기본 정보 (완료)' }));
    expect(screen.getByRole('heading', { name: '기본 정보' })).toBeInTheDocument();
    expect(screen.getByLabelText('연간 근로소득 (비과세 포함)')).toHaveValue('50,000,000');
  });
});
