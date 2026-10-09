import { describePath, formatDelta, formatInputValue } from './inputLabels';

describe('describePath', () => {
  it.each([
    ['income.annual_earned_income', '연간 근로소득'],
    ['credits.medical.general', '의료비 (그 밖의 부양가족)'],
    ['credits.donations.general', '일반기부금'],
    ['dependents[0]', '부양가족 1'],
    ['dependents[1].birth_year', '부양가족 2 · 출생연도'],
    ['credits.education[2].amount', '교육비 3 · 금액'],
    ['unknown.path', 'unknown.path'],
    ['dependents[0].unknown', '부양가족 1 · unknown'],
  ])('%s → %s', (path, expected) => {
    expect(describePath(path)).toBe(expected);
  });
});

describe('formatInputValue', () => {
  it.each([
    ['credits.irp', 3_000_000, '3,000,000원'],
    ['dependents[0].birth_year', 2012, '2012'],
    ['tax_year', 2026, '2026'],
    ['taxpayer.is_homeless', true, '예'],
    ['taxpayer.is_homeless', false, '아니오'],
    ['dependents[0].relation', 'lineal_ascendant', '직계존속 (부모·조부모)'],
    ['credits.education[0].kind', 'school', '초·중·고'],
    ['deductions.mortgage_type', 'other_15y', '15년 이상 · 그 밖의 대출'],
    ['deductions.mortgage_type', null, '없음'],
    ['dependents[0].name', '', '(빈 값)'],
    ['dependents[0].name', '첫째', '첫째'],
  ])('%s = %s → %s', (path, value, expected) => {
    expect(formatInputValue(path, value)).toBe(expected);
  });

  it('추가·삭제된 부양가족과 교육비를 요약한다', () => {
    expect(
      formatInputValue('dependents[1]', {
        name: '둘째',
        relation: 'lineal_descendant',
        birth_year: 2020,
      }),
    ).toBe('둘째 (직계비속 (자녀·손자녀), 2020년생)');
    expect(
      formatInputValue('credits.education[0]', { kind: 'university', amount: 9_000_000 }),
    ).toBe('대학생 9,000,000원');
    expect(formatInputValue('x', { a: 1 })).toBe('{"a":1}');
  });
});

describe('formatDelta', () => {
  it.each([
    [0, '0원'],
    [396000, '+396,000원'],
    [-360000, '−360,000원'],
  ])('%d → %s', (value, expected) => {
    expect(formatDelta(value)).toBe(expected);
  });
});
