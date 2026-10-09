import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../api/client';
import type { CoupleInput } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { SPOUSE_LABELS } from './schema';

/** 맞벌이 결과 우측: 최적 배분의 이유와 추가 팁을 AI가 설명한다 (배분·세액은 계산 엔진 결과). */
export function CoupleAiPanel({ input }: { input: CoupleInput | undefined }) {
  const [requestedFor, setRequestedFor] = useState<string | null>(null);
  const mutation = useMutation({ mutationFn: api.recommendCouple });
  const current = input ? JSON.stringify(input) : null;
  const data = mutation.data;
  const stale = data !== undefined && requestedFor !== current;

  return (
    <aside className="ai-panel" aria-label="AI 배분 설명" aria-busy={mutation.isPending}>
      <h2 className="ai-panel__title">✨ AI 배분 설명</h2>
      <p className="ai-panel__note">
        계산된 최적 배분이 왜 유리한지 AI가 설명하고 부부가 챙길 팁을 알려줍니다. 금액 정보(이름
        제외)가 OpenAI로 전송됩니다.
      </p>
      <button
        type="button"
        className="btn btn--primary ai-panel__button"
        disabled={!input || mutation.isPending}
        onClick={() => {
          if (!input) return;
          setRequestedFor(JSON.stringify(input));
          mutation.mutate(input);
        }}
      >
        {mutation.isPending ? 'AI가 분석 중…' : data ? '다시 설명 받기' : 'AI 설명 받기'}
      </button>
      <ApiErrorMessage error={mutation.error} />
      {data ? (
        <>
          {stale ? (
            <p className="alert alert--warning">입력이 바뀌었습니다. 다시 설명을 받아 보세요.</p>
          ) : null}
          <p className="ai-panel__summary">{data.summary}</p>
          <ul className="ai-panel__list">
            {data.dependent_reasons.map((r) => (
              <li key={r.index} className="ai-rec">
                <div className="ai-rec__head">
                  <span className="tag">{SPOUSE_LABELS[r.recommended_to]} 공제</span>
                  <strong className="ai-rec__title">{r.name}</strong>
                </div>
                <p className="ai-rec__text">{r.reason}</p>
              </li>
            ))}
          </ul>
          {data.tips.length > 0 ? (
            <>
              <h3 className="ai-panel__subtitle">부부 절세 팁</h3>
              <ul className="ai-panel__tips">
                {data.tips.map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
            </>
          ) : null}
          <p className="ai-panel__disclaimer">
            {data.disclaimer} · 모델 {data.model}
          </p>
        </>
      ) : null}
    </aside>
  );
}
