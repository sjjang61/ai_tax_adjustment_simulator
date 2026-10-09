import type { TaxResult } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { describeBalance, formatWon } from '../../lib/format';

export type PreviewComparison = { saving: number; changedCount: number };

type LivePreviewProps = {
  result: TaxResult | undefined;
  /** 저장된 시뮬레이션을 수정 중일 때: 저장본 대비 차이 (백엔드 비교 결과) */
  comparison?: PreviewComparison;
  isFetching: boolean;
  inputValid: boolean;
  error: unknown;
};

/** 입력 중 실시간 미리보기 (백엔드 계산 결과 표시). */
export function LivePreview({
  result,
  isFetching,
  inputValid,
  error,
  comparison,
}: LivePreviewProps) {
  const balance = result ? describeBalance(result.total_balance_due) : null;
  return (
    <aside className="preview" aria-label="실시간 미리보기" aria-busy={isFetching}>
      <h2 className="preview__title">실시간 미리보기</h2>
      {!inputValid ? (
        <p className="preview__hint">입력값을 확인하면 계산 결과가 표시됩니다.</p>
      ) : null}
      <ApiErrorMessage error={error} />
      {result && balance ? (
        <>
          <p className={`preview__balance preview__balance--${balance.kind}`}>
            <span>{balance.kind === 'none' ? '정산 결과' : `예상 ${balance.label}`}</span>
            <strong data-testid="preview-balance">{formatWon(balance.amount)}</strong>
          </p>
          <dl className="preview__list">
            <div>
              <dt>총급여</dt>
              <dd>{formatWon(result.gross_salary)}</dd>
            </div>
            <div>
              <dt>과세표준</dt>
              <dd>{formatWon(result.tax_base)}</dd>
            </div>
            <div>
              <dt>산출세액</dt>
              <dd>{formatWon(result.calculated_tax)}</dd>
            </div>
            <div>
              <dt>결정세액</dt>
              <dd>{formatWon(result.determined_tax)}</dd>
            </div>
            <div>
              <dt>기납부세액</dt>
              <dd>{formatWon(result.prepaid_tax)}</dd>
            </div>
          </dl>
          {comparison ? (
            <p
              className={`preview__compare preview__compare--${comparison.saving > 0 ? 'better' : comparison.saving < 0 ? 'worse' : 'same'}`}
              data-testid="preview-compare"
            >
              {comparison.changedCount === 0
                ? '저장본과 같음'
                : comparison.saving === 0
                  ? `저장본 대비 차이 없음 (입력 ${comparison.changedCount}개 변경)`
                  : `저장본 대비 ${formatWon(Math.abs(comparison.saving))} ${comparison.saving > 0 ? '유리' : '불리'} (입력 ${comparison.changedCount}개 변경)`}
            </p>
          ) : null}
          <p className="preview__hint preview__hint--small">
            아직 입력하지 않은 공제가 있으면 금액이 달라집니다.
          </p>
          <p className="preview__method">
            {result.applied_method === 'standard' ? '표준세액공제 적용' : '특별공제 적용'}
            {isFetching ? ' · 계산 중…' : ''}
          </p>
        </>
      ) : isFetching && inputValid ? (
        <p className="preview__hint">계산 중…</p>
      ) : null}
    </aside>
  );
}
