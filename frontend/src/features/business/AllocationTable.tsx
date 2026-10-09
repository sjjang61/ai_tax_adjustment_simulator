import type { BusinessAllocation } from '../../api/types';
import { formatWon } from '../../lib/format';

/** 사업장 소득금액의 공동사업자별 배분 (백엔드 계산 결과). */
export function AllocationTable({ allocation }: { allocation: BusinessAllocation }) {
  return (
    <section aria-label="지분별 배분">
      <h3>지분별 배분</h3>
      <p className="section__note">
        사업장 소득금액 {formatWon(allocation.income_amount)} (수입 {formatWon(allocation.revenue)}{' '}
        − 필요경비 {formatWon(allocation.expenses)}, {allocation.expense_note}) · 원천징수{' '}
        {formatWon(allocation.withholding_tax)}
      </p>
      <div className="table-scroll">
        <table className="compare-table income-table">
          <thead>
            <tr>
              <th scope="col">대표자</th>
              <th scope="col">지분</th>
              <th scope="col">수입금액</th>
              <th scope="col">필요경비</th>
              <th scope="col">소득금액</th>
              <th scope="col">원천징수</th>
            </tr>
          </thead>
          <tbody>
            {allocation.partners.map((p, i) => (
              <tr key={i}>
                <th scope="row">{p.name}</th>
                <td>
                  {p.ratio} <small className="muted">({p.share})</small>
                </td>
                <td>{formatWon(p.revenue)}</td>
                <td>{formatWon(p.expenses)}</td>
                <td>
                  <strong>{formatWon(p.income_amount)}</strong>
                </td>
                <td>{formatWon(p.withholding_tax)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
