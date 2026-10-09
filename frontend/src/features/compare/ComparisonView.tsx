import type { ItemDiff, SimulationComparison } from '../../api/types';
import { Disclaimer } from '../../components/Disclaimer';
import { formatWon } from '../../lib/format';
import { describePath, formatDelta, formatInputValue } from './inputLabels';

type ComparisonViewProps = {
  data: SimulationComparison;
  beforeLabel?: string;
  afterLabel?: string;
};

function ItemDiffTable({
  title,
  items,
  beforeLabel,
  afterLabel,
}: {
  title: string;
  items: readonly ItemDiff[];
  beforeLabel: string;
  afterLabel: string;
}) {
  if (items.length === 0) return null;
  return (
    <section aria-label={title}>
      <h3>{title}</h3>
      <table className="compare-table">
        <thead>
          <tr>
            <th scope="col">항목</th>
            <th scope="col">{beforeLabel}</th>
            <th scope="col">{afterLabel}</th>
            <th scope="col">차이</th>
          </tr>
        </thead>
        <tbody>
          {items.map((d) => (
            <tr key={d.key}>
              <th scope="row">{d.label}</th>
              <td>{formatWon(d.before)}</td>
              <td>{formatWon(d.after)}</td>
              <td className={d.delta > 0 ? 'delta--up' : 'delta--down'}>{formatDelta(d.delta)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

/** 기준(저장본)과 변경안의 결과·공제·입력 차이. 숫자는 모두 백엔드 계산 결과다. */
export function ComparisonView({
  data,
  beforeLabel = '저장본',
  afterLabel = '변경안',
}: ComparisonViewProps) {
  const c = data.comparison;
  const kind = c.saving > 0 ? 'better' : c.saving < 0 ? 'worse' : 'same';
  return (
    <div className="result compare">
      <Disclaimer />
      <section className={`summary compare-summary--${kind}`} aria-label="비교 요약">
        <p className="summary__label">
          {afterLabel}이(가) {beforeLabel} 대비 (지방소득세 포함)
        </p>
        <p className="summary__amount" data-testid="compare-saving">
          {kind === 'better'
            ? `${formatWon(c.saving)} 유리`
            : kind === 'worse'
              ? `${formatWon(-c.saving)} 불리`
              : '차이 없음'}
        </p>
        <p className="section__note">
          {kind === 'better'
            ? '환급이 늘거나 추가 납부가 줄어듭니다.'
            : kind === 'worse'
              ? '환급이 줄거나 추가 납부가 늘어납니다.'
              : '정산 결과가 같습니다.'}
        </p>
      </section>

      {data.snapshot_differs ? (
        <p className="alert alert--warning">
          저장 당시 결과와 현재 규칙으로 다시 계산한 결과가 다릅니다(세법 규칙 변경 등). 비교는 둘
          다 현재 규칙으로 계산한 값입니다.
        </p>
      ) : null}
      {c.tax_year_changed ? (
        <p className="alert alert--warning">
          귀속연도가 다릅니다 ({c.before.tax_year}년 → {c.after.tax_year}년). 세법 규칙 차이도
          결과에 반영됩니다.
        </p>
      ) : null}

      <section aria-label="주요 지표 비교">
        <h3>주요 지표</h3>
        <table className="compare-table">
          <thead>
            <tr>
              <th scope="col">항목</th>
              <th scope="col">{beforeLabel}</th>
              <th scope="col">{afterLabel}</th>
              <th scope="col">차이</th>
            </tr>
          </thead>
          <tbody>
            {c.metrics.map((m) => (
              <tr key={m.key} className={m.delta !== 0 ? 'is-changed' : undefined}>
                <th scope="row">{m.label}</th>
                <td>{formatWon(m.before)}</td>
                <td>{formatWon(m.after)}</td>
                <td>{formatDelta(m.delta)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section aria-label="바뀐 입력">
        <h3>바뀐 입력 ({c.input_diffs.length}개)</h3>
        {c.input_diffs.length === 0 ? (
          <p className="empty">바뀐 입력이 없습니다.</p>
        ) : (
          <ul className="compare-inputs">
            {c.input_diffs.map((d) => (
              <li key={d.path}>
                <span className="compare-inputs__label">{describePath(d.path)}</span>
                <span className="compare-inputs__values">
                  {formatInputValue(d.path, d.before)} →{' '}
                  <strong>{formatInputValue(d.path, d.after)}</strong>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <ItemDiffTable
        title="바뀐 소득공제"
        items={c.income_deduction_diffs}
        beforeLabel={beforeLabel}
        afterLabel={afterLabel}
      />
      <ItemDiffTable
        title="바뀐 세액공제"
        items={c.tax_credit_diffs}
        beforeLabel={beforeLabel}
        afterLabel={afterLabel}
      />
    </div>
  );
}
