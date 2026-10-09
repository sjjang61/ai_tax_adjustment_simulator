import type { CalcWarning } from '../api/types';

type WarningListProps = { warnings: readonly CalcWarning[]; title?: string };

/** 계산·이월 경고 목록. 요건 위반은 오류가 아닌 경고로 표시한다. */
export function WarningList({ warnings, title = '확인이 필요한 항목' }: WarningListProps) {
  if (warnings.length === 0) return null;
  return (
    <section className="warnings" aria-label={title}>
      <h3 className="warnings__title">{title}</h3>
      <ul>
        {warnings.map((w, i) => (
          <li key={`${w.code}-${i}`} className={`warnings__item warnings__item--${w.level}`}>
            <span className="warnings__badge">{w.level === 'info' ? '안내' : '주의'}</span>
            {w.message}
          </li>
        ))}
      </ul>
    </section>
  );
}
