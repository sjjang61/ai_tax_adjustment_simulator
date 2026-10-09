import type { BreakdownItem } from '../../api/types';
import { formatNumber, formatWon } from '../../lib/format';

function isVisible(item: BreakdownItem): boolean {
  return item.amount !== 0 || item.applied_amount !== 0 || item.children.some(isVisible);
}

function formatApplied(item: BreakdownItem): string {
  if (item.applied_unit === 'count') {
    // 인원·건수가 없는 항목(예: 표준세액공제)은 "0명/건" 대신 대시로 표시
    return item.applied_amount ? `${formatNumber(item.applied_amount)}명/건` : '—';
  }
  return formatWon(item.applied_amount);
}

function Row({ item, depth }: { item: BreakdownItem; depth: number }) {
  const children = item.children.filter(isVisible);
  return (
    <li className={`breakdown__item breakdown__item--depth-${depth}`}>
      <div className="breakdown__row">
        <span className="breakdown__label">
          {item.label}
          {item.limited ? <span className="badge badge--limit">한도·요건 적용</span> : null}
        </span>
        <span className="breakdown__applied" title="적용 대상">
          {formatApplied(item)}
        </span>
        <span className="breakdown__amount">{formatWon(item.amount)}</span>
      </div>
      {item.description ? <p className="breakdown__description">{item.description}</p> : null}
      {children.length > 0 ? (
        <ul className="breakdown__children">
          {children.map((child) => (
            <Row key={child.key} item={child} depth={depth + 1} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

type BreakdownTreeProps = { title: string; items: readonly BreakdownItem[]; total: number };

/** 공제 항목별 "적용 대상 → 공제액"과 근거 설명을 계층으로 보여준다. */
export function BreakdownTree({ title, items, total }: BreakdownTreeProps) {
  const visible = items.filter(isVisible);
  return (
    <section className="breakdown" aria-label={title}>
      <header className="breakdown__header">
        <h3>{title}</h3>
        <span className="breakdown__total">합계 {formatWon(total)}</span>
      </header>
      <div className="breakdown__columns" aria-hidden="true">
        <span>항목</span>
        <span>적용 대상</span>
        <span>공제액</span>
      </div>
      {visible.length === 0 ? (
        <p className="empty">해당 항목이 없습니다.</p>
      ) : (
        <ul className="breakdown__list">
          {visible.map((item) => (
            <Row key={item.key} item={item} depth={0} />
          ))}
        </ul>
      )}
    </section>
  );
}
