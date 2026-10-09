import type { TaxResult } from '../../api/types';
import { Disclaimer } from '../../components/Disclaimer';
import { WarningList } from '../../components/WarningList';
import { describeBalance, formatWon } from '../../lib/format';
import { BreakdownTree } from './BreakdownTree';

const METHOD_LABELS: Record<TaxResult['applied_method'], string> = {
  itemized: '특별공제 적용',
  standard: '표준세액공제',
};

function BalanceSummary({ result }: { result: TaxResult }) {
  const total = describeBalance(result.total_balance_due);
  const income = describeBalance(result.balance_due);
  const local = describeBalance(result.local_income_tax.balance_due);
  const tiles: [string, number][] = [
    ['결정세액', result.determined_tax],
    ['기납부세액', result.prepaid_tax],
    [`소득세 ${income.label}`, Math.abs(result.balance_due)],
    [`지방소득세 ${local.label}`, Math.abs(result.local_income_tax.balance_due)],
  ];
  return (
    <section className={`summary summary--${total.kind}`} aria-label="정산 결과 요약">
      <p className="summary__label">
        {total.kind === 'refund'
          ? '예상 환급액'
          : total.kind === 'payment'
            ? '예상 추가 납부액'
            : '정산 결과'}
        <small> (지방소득세 포함)</small>
      </p>
      <p className="summary__amount" data-testid="total-balance">
        {total.kind === 'none' ? '0원' : formatWon(total.amount)}
      </p>
      <dl className="stat-tiles">
        {tiles.map(([label, amount]) => (
          <div key={label} className="stat-tile">
            <dt>{label}</dt>
            <dd>{formatWon(amount)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

type FlowRow = { label: string; amount: number; note?: string; total?: boolean };

function CalculationFlow({ result }: { result: TaxResult }) {
  const rows: FlowRow[] = [
    { label: '연간 근로소득', amount: result.annual_earned_income },
    { label: '− 비과세소득', amount: result.non_taxable_income },
    { label: '= 총급여', amount: result.gross_salary, total: true },
    {
      label: '− 근로소득공제',
      amount: result.earned_income_deduction.amount,
      note: result.earned_income_deduction.description,
    },
    { label: '= 근로소득금액', amount: result.earned_income_amount, total: true },
    { label: '− 소득공제', amount: result.total_income_deduction },
    { label: '= 과세표준', amount: result.tax_base, total: true },
    {
      label: `× 기본세율 (${result.tax_rate} 구간)`,
      amount: result.calculated_tax,
      note: '산출세액',
    },
    { label: '− 세액감면', amount: result.tax_reduction },
    { label: '− 세액공제', amount: result.total_tax_credit },
    { label: '= 결정세액', amount: result.determined_tax, total: true },
    { label: '− 기납부세액', amount: result.prepaid_tax },
    {
      label: '= 차감징수세액 (소득세)',
      amount: result.balance_due,
      note: '음수면 환급',
      total: true,
    },
    {
      label: '지방소득세 결정세액',
      amount: result.local_income_tax.determined_tax,
      note: '소득세 결정세액 기준',
    },
  ];
  return (
    <section className="flow" aria-label="단계별 계산 내역">
      <h3>단계별 계산</h3>
      <ol className="flow__list">
        {rows.map((r) => (
          <li key={r.label} className={`flow__row${r.total ? ' flow__row--total' : ''}`}>
            <div className="flow__label">
              <span>{r.label}</span>
              {r.note ? <small className="flow__note">{r.note}</small> : null}
            </div>
            <span className="flow__amount">{formatWon(r.amount)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function MethodComparisonTable({ result }: { result: TaxResult }) {
  return (
    <section className="comparison" aria-label="공제 방식 비교">
      <h3>특별공제 vs 표준세액공제</h3>
      <p className="section__note">두 방식을 모두 계산해 결정세액이 적은 쪽을 자동 적용했습니다.</p>
      <div className="method-cards">
        {result.method_comparison.map((m) => {
          const applied = m.method === result.applied_method;
          return (
            <div key={m.method} className={`method-card${applied ? ' is-applied' : ''}`}>
              <p className="method-card__title">
                {METHOD_LABELS[m.method]}
                {applied ? <span className="badge badge--applied">적용</span> : null}
              </p>
              <dl>
                <div>
                  <dt>과세표준</dt>
                  <dd>{formatWon(m.tax_base)}</dd>
                </div>
                <div>
                  <dt>세액공제</dt>
                  <dd>{formatWon(m.total_tax_credit)}</dd>
                </div>
                <div className="method-card__total">
                  <dt>결정세액</dt>
                  <dd>{formatWon(m.determined_tax)}</dd>
                </div>
              </dl>
            </div>
          );
        })}
      </div>
    </section>
  );
}

/** 결과·계산 내역 화면. 숫자는 모두 백엔드 계산 결과를 그대로 표시한다. */
export function ResultView({ result }: { result: TaxResult }) {
  return (
    <div className="result">
      <BalanceSummary result={result} />
      <Disclaimer text={result.disclaimer} />
      {!result.rules_verified ? (
        <p className="alert alert--warning">
          {result.tax_year}년 귀속 세법 규칙은 아직 공식 자료로 검증되지 않았습니다.
        </p>
      ) : null}
      <WarningList warnings={result.warnings} />
      <CalculationFlow result={result} />
      <MethodComparisonTable result={result} />
      <BreakdownTree
        title="소득공제"
        items={result.income_deductions}
        total={result.total_income_deduction}
      />
      <BreakdownTree title="세액공제" items={result.tax_credits} total={result.total_tax_credit} />
    </div>
  );
}
