/**
 * 금액 표시·입력 변환 유틸.
 * 금액은 항상 원 단위 정수로 저장하고, 표시할 때만 천 단위 콤마를 붙인다.
 * 세액 계산은 하지 않는다 (백엔드 책임).
 */

const numberFormatter = new Intl.NumberFormat('ko-KR');

export function formatNumber(value: number): string {
  return numberFormatter.format(value);
}

/** 1234567 → "1,234,567원" */
export function formatWon(value: number): string {
  return `${formatNumber(value)}원`;
}

/** 소수 문자열을 10^zeros 배 한 정수로 변환 (부동소수 오차 없이, 초과 자릿수는 절사). */
function scaleDecimal(text: string, zeros: number): number | null {
  const match = /^(\d*)(?:\.(\d*))?$/.exec(text);
  if (!match || (match[1] === '' && (match[2] ?? '') === '')) return null;
  const intPart = match[1] ?? '';
  const fracPart = (match[2] ?? '').padEnd(zeros, '0').slice(0, zeros);
  return Number(`${intPart || '0'}${fracPart}`);
}

const UNITS: Record<string, number> = { 억: 8, 만: 4 };

/**
 * 사용자 입력을 원 단위 정수로 변환한다.
 * - "1,234,567", "1234567원" → 1234567
 * - "3000만", "3,000만원" → 30000000
 * - "1.5억", "1억 2,000만" → 150000000, 120000000
 * - 빈 문자열 → 0, 해석 불가 → null
 */
export function parseAmount(input: string): number | null {
  const text = input.replace(/[,\s]/g, '').replace(/원$/, '');
  if (text === '') return 0;
  let total = 0;
  let rest = text;
  for (const [unit, zeros] of Object.entries(UNITS)) {
    const idx = rest.indexOf(unit);
    if (idx === -1) continue;
    const scaled = scaleDecimal(rest.slice(0, idx), zeros);
    if (scaled === null) return null;
    total += scaled;
    rest = rest.slice(idx + 1);
  }
  if (rest !== '') {
    if (!/^\d+$/.test(rest)) return null;
    total += Number(rest);
  }
  return Number.isSafeInteger(total) ? total : null;
}

/** 만원 단위 숫자(소수 허용) → 원. 3000.5 → 30005000 */
export function manwonToWon(manwon: number): number {
  const scaled = scaleDecimal(String(manwon), 4);
  if (scaled === null) throw new Error(`잘못된 만원 금액: ${manwon}`);
  return scaled;
}

/** 원 → 읽기 쉬운 한국어 단위. 123456789 → "1억 2,345만 6,789원" */
export function formatKoreanUnit(value: number): string {
  if (value === 0) return '0원';
  const sign = value < 0 ? '-' : '';
  let rest = Math.abs(value);
  const eok = Math.floor(rest / 100_000_000);
  rest -= eok * 100_000_000;
  const man = Math.floor(rest / 10_000);
  const won = rest - man * 10_000;
  const parts: string[] = [];
  if (eok) parts.push(`${formatNumber(eok)}억`);
  if (man) parts.push(`${formatNumber(man)}만`);
  if (won) parts.push(formatNumber(won));
  return `${sign}${parts.join(' ')}원`;
}

export type BalanceKind = 'refund' | 'payment' | 'none';

/** 차감징수세액(음수 = 환급) 표시용 분류. */
export function describeBalance(value: number): {
  kind: BalanceKind;
  label: string;
  amount: number;
} {
  if (value < 0) return { kind: 'refund', label: '환급', amount: -value };
  if (value > 0) return { kind: 'payment', label: '추가 납부', amount: value };
  return { kind: 'none', label: '납부·환급 없음', amount: 0 };
}

/** 규칙 비율 문자열("0.15") → "15%" (표시 전용). */
export function formatRate(rate: string): string {
  const percent = scaleDecimal(rate, 6);
  if (percent === null) return rate;
  // percent는 rate × 10^6, 퍼센트는 rate × 10^2 → 10^4로 나눈 값을 소수 4자리까지 표시
  const value = percent / 10_000;
  return `${Number(value.toFixed(4))}%`;
}
