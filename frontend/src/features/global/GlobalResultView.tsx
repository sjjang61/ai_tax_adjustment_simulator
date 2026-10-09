import type { GlobalIncomeResult, IncomeLine } from '../../api/types';
import { Disclaimer } from '../../components/Disclaimer';
import { WarningList } from '../../components/WarningList';
import { describeBalance, formatWon } from '../../lib/format';
import { BreakdownTree } from '../result/BreakdownTree';

const KIND_LABELS: Record<IncomeLine['kind'], string> = {
  earned: '근로',
  business: '사업',
  other: '기타',
};

const TAXATION_LABELS = { comprehensive: '종합과세', separate: '분리과세' } as const;

/** 종합소득세 결과. 숫자는 모두 백엔드 계산 결과다. */
export function GlobalResultView({ result }: { result: GlobalIncomeResult }) {
  const total = describeBalance(result.total_balance_due);
  const r = result.tax_result;
  const p = result.prepaid;
  const flow: { label: string; amount: number; note?: string; total?: boolean }[] = [
    { label: '근로소득금액', amount: result.earned_income_amount },
    { label: '+ 사업소득금액', amount: result.business_income_amount },
    {
      label: '+ 기타소득금액 (종합과세분)',
      amount: result.other_income_amount,
      note:
        result.other_income_taxation === 'separate' ? '분리과세 선택 → 합산하지 않음' : undefined,
    },
    { label: '= 종합소득금액', amount: result.comprehensive_income_amount, total: true },
    { label: '− 소득공제', amount: r.total_income_deduction },
    { label: '= 과세표준', amount: r.tax_base, total: true },
    { label: `× 기본세율 (${r.tax_rate} 구간)`, amount: r.calculated_tax, note: '산출세액' },
    { label: '− 세액공제', amount: r.total_tax_credit },
    { label: '= 결정세액', amount: r.determined_tax, total: true },
    { label: '− 기납부세액', amount: p.total },
    { label: '= 납부할 세액 (소득세)', amount: r.balance_due, note: '음수면 환급', total: true },
    {
      label: '지방소득세 결정세액',
      amount: r.local_income_tax.determined_tax,
      note: '소득세 결정세액 기준',
    },
  ];

  return (
    <div className="result">
      <section className={`summary summary--${total.kind}`} aria-label="종합소득세 결과 요약">
        <p className="summary__label">
          {total.kind === 'refund'
            ? '예상 환급액'
            : total.kind === 'payment'
              ? '예상 납부액'
              : '정산 결과'}
          <small> (지방소득세 포함)</small>
        </p>
        <p className="summary__amount" data-testid="global-total">
          {total.kind === 'none' ? '0원' : formatWon(total.amount)}
        </p>
        <dl className="stat-tiles">
          <div className="stat-tile">
            <dt>종합소득금액</dt>
            <dd>{formatWon(result.comprehensive_income_amount)}</dd>
          </div>
          <div className="stat-tile">
            <dt>결정세액</dt>
            <dd>{formatWon(r.determined_tax)}</dd>
          </div>
          <div className="stat-tile">
            <dt>기납부세액</dt>
            <dd>{formatWon(p.total)}</dd>
          </div>
          {result.separate_tax ? (
            <div className="stat-tile">
              <dt>분리과세 기타소득세</dt>
              <dd>{formatWon(result.separate_tax)}</dd>
            </div>
          ) : null}
        </dl>
      </section>
      <Disclaimer text={result.disclaimer} />
      {!result.rules_verified ? (
        <p className="alert alert--warning">
          {result.tax_year}년 귀속 세법 규칙은 아직 공식 자료로 검증되지 않았습니다.
        </p>
      ) : null}
      <WarningList warnings={result.warnings} />

      <section aria-label="소득별 내역">
        <h3>소득별 내역</h3>
        <div className="table-scroll">
          <table className="compare-table income-table">
            <thead>
              <tr>
                <th scope="col">소득</th>
                <th scope="col">수입금액</th>
                <th scope="col">필요경비</th>
                <th scope="col">소득금액</th>
                <th scope="col">원천징수·기납부</th>
              </tr>
            </thead>
            <tbody>
              {result.income_lines.map((line, i) => (
                <tr key={`${line.kind}-${i}`}>
                  <th scope="row">
                    <span className={`tag tag--${line.kind}`}>{KIND_LABELS[line.kind]}</span>{' '}
                    {line.name}
                    {line.note ? <small className="flow__note"> {line.note}</small> : null}
                  </th>
                  <td>{formatWon(line.revenue)}</td>
                  <td>{formatWon(line.expenses)}</td>
                  <td>{formatWon(line.income_amount)}</td>
                  <td>{formatWon(line.withholding_tax)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {result.options.length > 1 ? (
        <section className="comparison" aria-label="기타소득 과세 방법 비교">
          <h3>기타소득 종합과세 vs 분리과세</h3>
          <div className="method-cards">
            {result.options.map((o) => {
              const applied = o.taxation === result.other_income_taxation;
              return (
                <div key={o.taxation} className={`method-card${applied ? ' is-applied' : ''}`}>
                  <p className="method-card__title">
                    {TAXATION_LABELS[o.taxation]}
                    {applied ? <span className="badge badge--applied">적용</span> : null}
                  </p>
                  <dl>
                    <div>
                      <dt>종합소득 결정세액</dt>
                      <dd>{formatWon(o.determined_tax)}</dd>
                    </div>
                    <div>
                      <dt>분리과세 세액</dt>
                      <dd>{formatWon(o.separate_tax)}</dd>
                    </div>
                    <div className="method-card__total">
                      <dt>총 세부담 (지방소득세 포함)</dt>
                      <dd>{formatWon(o.total_burden)}</dd>
                    </div>
                  </dl>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      <section className="flow" aria-label="종합소득세 계산 흐름">
        <h3>단계별 계산</h3>
        <ol className="flow__list">
          {flow.map((row) => (
            <li key={row.label} className={`flow__row${row.total ? ' flow__row--total' : ''}`}>
              <div className="flow__label">
                <span>{row.label}</span>
                {row.note ? <small className="flow__note">{row.note}</small> : null}
              </div>
              <span className="flow__amount">{formatWon(row.amount)}</span>
            </li>
          ))}
        </ol>
      </section>

      <section aria-label="기납부세액 내역">
        <h3>기납부세액 내역</h3>
        <ol className="flow__list">
          {[
            ['근로소득 (연말정산 결정세액)', p.earned_settled],
            ['사업소득 원천징수', p.business_withholding],
            ['기타소득 원천징수 (종합과세분)', p.other_withholding],
            ['중간예납', p.interim_prepayment],
          ].map(([label, amount]) => (
            <li key={label as string} className="flow__row">
              <div className="flow__label">
                <span>{label}</span>
              </div>
              <span className="flow__amount">{formatWon(amount as number)}</span>
            </li>
          ))}
          <li className="flow__row flow__row--total">
            <div className="flow__label">
              <span>합계</span>
            </div>
            <span className="flow__amount">{formatWon(p.total)}</span>
          </li>
        </ol>
      </section>

      <BreakdownTree
        title="소득공제"
        items={r.income_deductions}
        total={r.total_income_deduction}
      />
      <BreakdownTree title="세액공제" items={r.tax_credits} total={r.total_tax_credit} />
    </div>
  );
}
