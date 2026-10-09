import {
  describeBalance,
  formatKoreanUnit,
  formatNumber,
  formatRate,
  formatWon,
  manwonToWon,
  parseAmount,
} from './format';

describe('formatWon / formatNumber', () => {
  it.each([
    [0, '0원'],
    [999, '999원'],
    [1000, '1,000원'],
    [1234567, '1,234,567원'],
    [-636300, '-636,300원'],
  ])('%d → %s', (value, expected) => {
    expect(formatWon(value)).toBe(expected);
  });

  it('formatNumber는 단위 없이 콤마만 붙인다', () => {
    expect(formatNumber(50000000)).toBe('50,000,000');
  });
});

describe('parseAmount', () => {
  it.each([
    ['', 0],
    ['0', 0],
    ['1,234,567', 1234567],
    ['1234567원', 1234567],
    [' 12 345 ', 12345],
    ['3000만', 30000000],
    ['3,000만원', 30000000],
    ['0.5만', 5000],
    ['1.5억', 150000000],
    ['1억 2,000만', 120000000],
    ['1억2000만5000', 120005000],
    ['1.23456만', 12345], // 원 미만 절사
  ])('"%s" → %d', (input, expected) => {
    expect(parseAmount(input)).toBe(expected);
  });

  it.each(['abc', '-1000', '1.5', '만', '1만x', '12a원', '9999999999999999999'])(
    '"%s"는 해석 불가(null)',
    (input) => {
      expect(parseAmount(input)).toBeNull();
    },
  );
});

describe('manwonToWon', () => {
  it.each([
    [0, 0],
    [3000, 30000000],
    [1.005, 10050], // 부동소수 오차 없이 변환
    [0.29, 2900],
    [3000.5, 30005000],
  ])('%d만원 → %d원', (manwon, expected) => {
    expect(manwonToWon(manwon)).toBe(expected);
  });

  it('음수는 거부한다', () => {
    expect(() => manwonToWon(-1)).toThrow();
  });
});

describe('formatKoreanUnit', () => {
  it.each([
    [0, '0원'],
    [6789, '6,789원'],
    [30000000, '3,000만원'],
    [123456789, '1억 2,345만 6,789원'],
    [100000000, '1억원'],
    [-50000, '-5만원'],
  ])('%d → %s', (value, expected) => {
    expect(formatKoreanUnit(value)).toBe(expected);
  });
});

describe('describeBalance', () => {
  it('음수는 환급', () => {
    expect(describeBalance(-636300)).toEqual({ kind: 'refund', label: '환급', amount: 636300 });
  });
  it('양수는 추가 납부', () => {
    expect(describeBalance(1000)).toEqual({ kind: 'payment', label: '추가 납부', amount: 1000 });
  });
  it('0은 없음', () => {
    expect(describeBalance(0).kind).toBe('none');
  });
});

describe('formatRate', () => {
  it.each([
    ['0.15', '15%'],
    ['0.70', '70%'],
    ['0.008', '0.8%'],
    ['0.9090909090909090909090909091', '90.909%'],
    ['x', 'x'],
  ])('%s → %s', (rate, expected) => {
    expect(formatRate(rate)).toBe(expected);
  });
});
