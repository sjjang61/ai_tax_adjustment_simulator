import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../api/client';
import type { Recommendation, RecommendationCategory, SimulationInput } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { formatWon } from '../../lib/format';

const CATEGORY_LABELS: Record<RecommendationCategory, string> = {
  income_deduction: '소득공제',
  tax_credit: '세액공제',
  eligibility_check: '확인 필요',
  other: '기타',
};

type AiRecommendationsProps = {
  /** 현재 형식 검증을 통과한 입력. 없으면 추천을 요청할 수 없다. */
  input: SimulationInput | undefined;
  /** 추천을 반영한 입력으로 폼을 바꾼다. */
  onApply: (input: SimulationInput) => void;
};

function RecommendationCard({
  rec,
  onApply,
}: {
  rec: Recommendation;
  onApply: (input: SimulationInput) => void;
}) {
  return (
    <li className="ai-rec">
      <div className="ai-rec__head">
        <span className={`tag tag--${rec.category}`}>{CATEGORY_LABELS[rec.category]}</span>
        <strong className="ai-rec__title">{rec.title}</strong>
      </div>
      {rec.estimated_saving !== null && rec.estimated_saving !== undefined ? (
        <p className="ai-rec__saving">
          예상 절세 <strong>{formatWon(rec.estimated_saving)}</strong>
          <small> (지방소득세 포함)</small>
        </p>
      ) : null}
      <p className="ai-rec__text">{rec.reason}</p>
      <p className="ai-rec__action">
        <span aria-hidden="true">👉 </span>
        {rec.action}
      </p>
      {rec.adjusted_input && rec.adjustment_label && rec.additional_amount ? (
        <div className="ai-rec__adjust">
          <span>
            {rec.adjustment_label} +{formatWon(rec.additional_amount)}
          </span>
          <button
            type="button"
            className="btn btn--secondary btn--small"
            onClick={() => rec.adjusted_input && onApply(rec.adjusted_input)}
          >
            적용해 보기
          </button>
        </div>
      ) : null}
    </li>
  );
}

/** 결과 화면 우측: AI가 추가로 받을 수 있는 공제 항목을 추천한다 (절세액은 백엔드 계산 엔진이 산출). */
export function AiRecommendations({ input, onApply }: AiRecommendationsProps) {
  const [requestedFor, setRequestedFor] = useState<string | null>(null);
  const [previous, setPrevious] = useState<SimulationInput | null>(null);
  const mutation = useMutation({ mutationFn: api.recommend });
  const current = input ? JSON.stringify(input) : null;
  const stale = mutation.data !== undefined && requestedFor !== current;

  const request = () => {
    if (!input) return;
    setRequestedFor(JSON.stringify(input));
    mutation.mutate(input);
  };

  const apply = (adjusted: SimulationInput) => {
    if (input) setPrevious(input);
    onApply(adjusted);
  };

  const data = mutation.data;
  return (
    <aside className="ai-panel" aria-label="AI 추천" aria-busy={mutation.isPending}>
      <h2 className="ai-panel__title">✨ AI 추천</h2>
      <p className="ai-panel__note">
        현재 결과를 바탕으로 추가로 받을 수 있는 공제를 추천합니다. 입력한 금액 정보(이름 제외)가
        OpenAI로 전송됩니다.
      </p>
      <button
        type="button"
        className="btn btn--primary ai-panel__button"
        onClick={request}
        disabled={!input || mutation.isPending}
      >
        {mutation.isPending ? 'AI가 분석 중…' : data ? '다시 추천 받기' : 'AI 추천 받기'}
      </button>
      {!input ? <p className="preview__hint">입력값 오류를 먼저 해결하세요.</p> : null}

      {previous ? (
        <div className="ai-panel__applied" role="status">
          추천을 적용해 결과를 다시 계산했습니다.
          <button
            type="button"
            className="btn btn--ghost btn--small"
            onClick={() => {
              onApply(previous);
              setPrevious(null);
            }}
          >
            되돌리기
          </button>
        </div>
      ) : null}

      <ApiErrorMessage error={mutation.error} />

      {data ? (
        <>
          {stale ? (
            <p className="alert alert--warning">입력이 바뀌었습니다. 다시 추천을 받아 보세요.</p>
          ) : null}
          <p className="ai-panel__summary">{data.summary}</p>
          {data.recommendations.length === 0 ? (
            <p className="empty">추가로 추천할 항목이 없습니다.</p>
          ) : (
            <ul className="ai-panel__list">
              {data.recommendations.map((rec, i) => (
                <RecommendationCard key={`${rec.title}-${i}`} rec={rec} onApply={apply} />
              ))}
            </ul>
          )}
          <p className="ai-panel__disclaimer">
            {data.disclaimer} · 모델 {data.model}
          </p>
        </>
      ) : null}
    </aside>
  );
}
