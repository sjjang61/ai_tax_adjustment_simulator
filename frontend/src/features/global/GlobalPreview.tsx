import type { GlobalIncomeResult } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { describeBalance, formatWon } from '../../lib/format';

type GlobalPreviewProps = {
  result: GlobalIncomeResult | undefined;
  isFetching: boolean;
  inputValid: boolean;
  error: unknown;
};

/** 종합소득세 실시간 미리보기 (백엔드 계산 결과 표시). */
export function GlobalPreview({ result, isFetching, inputValid, error }: GlobalPreviewProps) {
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
            <span>
              {balance.kind === 'refund'
                ? '예상 환급'
                : balance.kind === 'payment'
                  ? '예상 납부'
                  : '납부·환급 없음'}
            </span>
            <strong data-testid="global-preview-balance">{formatWon(balance.amount)}</strong>
          </p>
          <dl className="preview__list">
            <div>
              <dt>종합소득금액</dt>
              <dd>{formatWon(result.comprehensive_income_amount)}</dd>
            </div>
            <div>
              <dt>과세표준</dt>
              <dd>{formatWon(result.tax_result.tax_base)}</dd>
            </div>
            <div>
              <dt>결정세액</dt>
              <dd>{formatWon(result.tax_result.determined_tax)}</dd>
            </div>
            <div>
              <dt>기납부세액</dt>
              <dd>{formatWon(result.prepaid.total)}</dd>
            </div>
          </dl>
          <p className="preview__hint preview__hint--small">지방소득세 포함 금액입니다.</p>
        </>
      ) : isFetching && inputValid ? (
        <p className="preview__hint">계산 중…</p>
      ) : null}
    </aside>
  );
}
