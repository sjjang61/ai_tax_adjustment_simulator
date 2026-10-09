import { QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import type { SimulationInput } from '../../api/types';
import { BASE, fixtureInput } from '../../test/handlers';
import { createTestQueryClient } from '../../test/render';
import { server } from '../../test/server';
import { AiRecommendations } from './AiRecommendations';

function renderPanel(input: SimulationInput | undefined, onApply = vi.fn()) {
  const client = createTestQueryClient();
  const utils = render(
    <QueryClientProvider client={client}>
      <AiRecommendations input={input} onApply={onApply} />
    </QueryClientProvider>,
  );
  const rerender = (next: SimulationInput | undefined) =>
    utils.rerender(
      <QueryClientProvider client={client}>
        <AiRecommendations input={next} onApply={onApply} />
      </QueryClientProvider>,
    );
  return { onApply, rerender };
}

describe('AiRecommendations', () => {
  it('버튼을 눌러야 요청하고, 엔진이 계산한 절세액과 확인 항목을 보여준다', async () => {
    const user = userEvent.setup();
    let sent: SimulationInput | null = null;
    server.events.on('request:start', async ({ request }) => {
      if (request.url.endsWith('/recommendations'))
        sent = (await request.clone().json()) as SimulationInput;
    });
    renderPanel(fixtureInput);
    expect(screen.getByText(/OpenAI로 전송됩니다/)).toBeInTheDocument();
    expect(sent).toBeNull(); // 자동 전송 없음

    await user.click(screen.getByRole('button', { name: 'AI 추천 받기' }));
    expect(await screen.findByText('IRP 추가 납입')).toBeInTheDocument();
    expect(screen.getByText('396,000원')).toBeInTheDocument();
    expect(screen.getByText('부양가족 등록 확인')).toBeInTheDocument();
    expect(screen.getByText('확인 필요')).toBeInTheDocument();
    expect(screen.getByText(/모델 gpt-5.6-luna/)).toBeInTheDocument();
    expect(sent).toEqual(fixtureInput);
    server.events.removeAllListeners();
  });

  it('추천을 적용하고 되돌릴 수 있다', async () => {
    const user = userEvent.setup();
    const { onApply } = renderPanel(fixtureInput);
    await user.click(screen.getByRole('button', { name: 'AI 추천 받기' }));
    await user.click(await screen.findByRole('button', { name: '적용해 보기' }));
    expect(onApply).toHaveBeenLastCalledWith(
      expect.objectContaining({ credits: expect.objectContaining({ irp: 3_000_000 }) }),
    );
    await user.click(screen.getByRole('button', { name: '되돌리기' }));
    expect(onApply).toHaveBeenLastCalledWith(fixtureInput);
  });

  it('입력이 바뀌면 다시 받으라고 안내한다', async () => {
    const user = userEvent.setup();
    const { rerender } = renderPanel(fixtureInput);
    await user.click(screen.getByRole('button', { name: 'AI 추천 받기' }));
    await screen.findByText('IRP 추가 납입');
    rerender({ ...fixtureInput, prepaid_tax: { withholding: 1, previous_employer: 0 } });
    expect(screen.getByText('입력이 바뀌었습니다. 다시 추천을 받아 보세요.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '다시 추천 받기' })).toBeEnabled();
  });

  it('입력 오류가 있으면 요청할 수 없다', () => {
    renderPanel(undefined);
    expect(screen.getByRole('button', { name: 'AI 추천 받기' })).toBeDisabled();
  });

  it('AI 미설정 오류를 표시한다', async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${BASE}/recommendations`, () =>
        HttpResponse.json(
          { code: 'ai_unavailable', message: 'OPENAI_API_KEY를 설정해야 합니다.', details: null },
          { status: 503 },
        ),
      ),
    );
    renderPanel(fixtureInput);
    await user.click(screen.getByRole('button', { name: 'AI 추천 받기' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('OPENAI_API_KEY');
  });
});
