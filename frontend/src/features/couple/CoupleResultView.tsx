import type { CoupleInput, CoupleOptimizationResult, PlanSummary, Spouse } from '../../api/types';
import { Disclaimer } from '../../components/Disclaimer';
import { WarningList } from '../../components/WarningList';
import { describeBalance, formatWon } from '../../lib/format';
import { RELATION_LABELS } from '../simulation/defaults';
import { ResultView } from '../result/ResultView';
import { SPOUSE_LABELS } from './schema';

function balanceText(value: number): string {
  const b = describeBalance(value);
  return b.kind === 'none' ? '0원' : `${b.label} ${formatWon(b.amount)}`;
}

function PlanTable({ baseline, best }: { baseline: PlanSummary; best: PlanSummary }) {
  const rows: [string, (p: PlanSummary) => string][] = [
    ['본인 결정세액', (p) => formatWon(p.primary_determined_tax)],
    ['배우자 결정세액', (p) => formatWon(p.spouse_determined_tax)],
    ['부부 합산 결정세액', (p) => formatWon(p.combined_determined_tax)],
    ['부부 합산 지방소득세', (p) => formatWon(p.combined_local_income_tax)],
    ['부부 합산 정산 결과', (p) => balanceText(p.combined_total_balance_due)],
  ];
  return (
    <table className="couple-table">
      <thead>
        <tr>
          <th scope="col">구분</th>
          <th scope="col">현재 배분</th>
          <th scope="col">추천 배분</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([label, fn]) => (
          <tr key={label}>
            <th scope="row">{label}</th>
            <td>{fn(baseline)}</td>
            <td className="is-applied">{fn(best)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

type CoupleResultViewProps = {
  input: CoupleInput;
  result: CoupleOptimizationResult;
  onApplyBest: () => void;
};

/** 맞벌이 최적 배분 결과. 모든 숫자는 백엔드 계산 엔진 결과다. */
export function CoupleResultView({ input, result, onApplyBest }: CoupleResultViewProps) {
  const deps = input.shared_dependents;
  const changed = result.best.assignment.some((a, i) => a !== result.baseline.assignment[i]);
  return (
    <div className="result couple-result">
      <Disclaimer />
      <section
        className={`summary ${result.saving > 0 ? 'summary--refund' : ''}`}
        aria-label="최적 배분 요약"
      >
        <p className="summary__label">
          {result.saving > 0 ? '추천 배분으로 바꾸면 부부 합산' : '현재 배분이 가장 유리합니다'}
        </p>
        <p className="summary__amount" data-testid="couple-saving">
          {result.saving > 0 ? `${formatWon(result.saving)} 절세` : '변경 불필요'}
        </p>
        <p className="section__note">
          가능한 {result.evaluated_count.toLocaleString('ko-KR')}가지 배분을 모두 계산했습니다
          (지방소득세 포함).
        </p>
      </section>

      {deps.length > 0 ? (
        <section aria-label="부양가족 배분">
          <h3>부양가족 배분</h3>
          <table className="couple-table">
            <thead>
              <tr>
                <th scope="col">가족</th>
                <th scope="col">현재</th>
                <th scope="col">추천</th>
              </tr>
            </thead>
            <tbody>
              {deps.map((d, i) => {
                const best = result.best.assignment[i] as Spouse;
                const base = result.baseline.assignment[i] as Spouse;
                return (
                  <tr key={i}>
                    <th scope="row">
                      {d.name || `부양가족 ${i + 1}`}{' '}
                      <small className="muted">({RELATION_LABELS[d.relation]})</small>
                    </th>
                    <td>{SPOUSE_LABELS[base]}</td>
                    <td>
                      <strong>{SPOUSE_LABELS[best]}</strong>
                      {best !== base ? <span className="badge badge--applied">변경</span> : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {changed ? (
            <button type="button" className="btn btn--secondary" onClick={onApplyBest}>
              추천 배분을 현재 배분으로 적용
            </button>
          ) : null}
        </section>
      ) : null}

      <section aria-label="배분별 세액 비교">
        <h3>현재 vs 추천</h3>
        <PlanTable baseline={result.baseline} best={result.best} />
      </section>

      {result.alternatives.length > 0 ? (
        <section aria-label="다른 배분안">
          <h3>다른 배분안</h3>
          <ul className="couple-alts">
            {result.alternatives.map((alt, i) => (
              <li key={i}>
                {deps
                  .map(
                    (d, j) =>
                      `${d.name || `부양가족 ${j + 1}`}→${SPOUSE_LABELS[alt.assignment[j] as Spouse]}`,
                  )
                  .join(', ')}
                <span>
                  {balanceText(alt.combined_total_balance_due)} (추천안 대비{' '}
                  {formatWon(
                    alt.combined_total_balance_due - result.best.combined_total_balance_due,
                  )}{' '}
                  불리)
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <WarningList
        warnings={[...result.best_primary_result.warnings, ...result.best_spouse_result.warnings]}
      />

      <details className="couple-detail">
        <summary>본인 상세 계산 (추천 배분)</summary>
        <ResultView result={result.best_primary_result} />
      </details>
      <details className="couple-detail">
        <summary>배우자 상세 계산 (추천 배분)</summary>
        <ResultView result={result.best_spouse_result} />
      </details>
    </div>
  );
}
