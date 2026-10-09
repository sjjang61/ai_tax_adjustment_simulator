import type { SimulationInput } from '../../api/types';
import { emptyInput } from '../simulation/defaults';
import { importIndividual } from './importIndividual';
import { newSharedDependent, type SharedDependentFormValue } from './schema';

function individual(overrides: Partial<SimulationInput> = {}): SimulationInput {
  const base = emptyInput(2025);
  return {
    ...base,
    income: { annual_earned_income: 60_000_000, non_taxable_income: 2_400_000 },
    prepaid_tax: { withholding: 3_000_000, previous_employer: 0 },
    taxpayer: { ...base.taxpayer, birth_year: 1985, is_female: true },
    deductions: { ...base.deductions, national_pension: 2_000_000 },
    credits: { ...base.credits, irp: 3_000_000 },
    ...overrides,
  };
}

const child = {
  name: '첫째',
  relation: 'lineal_descendant' as const,
  birth_year: 2015,
  disabled: false,
  income_amount: 0,
  income_is_salary_only: false,
  born_or_adopted_this_year: false,
  child_order: null,
};

describe('importIndividual', () => {
  it('급여·공제는 개인 몫으로, 부양가족은 부양가족 배분으로 옮긴다', () => {
    const src = individual({
      dependents: [
        child,
        { ...child, name: '어머니', relation: 'lineal_ascendant', birth_year: 1955 },
      ],
    });
    const r = importIndividual(src, 'spouse', [], 2025);

    expect(r.person.income.annual_earned_income).toBe(60_000_000);
    expect(r.person.prepaid_tax.withholding).toBe(3_000_000);
    expect(r.person.credits.irp).toBe(3_000_000);
    expect(r.person.taxpayer.is_married).toBe(true);
    expect(r.person.taxpayer.is_female).toBe(true);
    expect(r.person.dependents).toEqual([]);

    expect(r.added.map((d) => [d.name, d.relation, d.assigned_to])).toEqual([
      ['첫째', 'lineal_descendant', 'spouse'],
      ['어머니', 'lineal_ascendant', 'spouse'],
    ]);
    expect(r.notes).toContain(
      '부양가족 2명을 「부양가족 배분」 단계로 옮겼습니다 (현재 공제: 배우자).',
    );
    expect(src.dependents).toHaveLength(2); // 원본 불변
  });

  it('배우자로 등록된 부양가족은 제외한다', () => {
    const r = importIndividual(
      individual({
        dependents: [{ ...child, name: '남편', relation: 'spouse', birth_year: 1984 }],
      }),
      'primary',
      [],
      2025,
    );
    expect(r.added).toEqual([]);
    expect(
      r.notes.some((n) => n.includes('배우자(남편)는 맞벌이 입력에서 각자 입력하므로 제외')),
    ).toBe(true);
  });

  it('이미 있는 부양가족(이름·관계·출생연도 동일)은 중복 추가하지 않는다', () => {
    const existing: SharedDependentFormValue[] = [
      { ...newSharedDependent(), name: '첫째', relation: 'lineal_descendant', birth_year: 2015 },
    ];
    const r = importIndividual(individual({ dependents: [child] }), 'spouse', existing, 2025);
    expect(r.added).toEqual([]);
    expect(
      r.notes.some((n) => n.includes('첫째는 이미 「부양가족 배분」에 있어 추가하지 않았습니다')),
    ).toBe(true);
  });

  it('대상자 이름이 부양가족과 같은 교육비는 그 가족으로 옮기고, 나머지는 개인 몫에 남긴다', () => {
    const base = emptyInput(2025);
    const src = individual({
      dependents: [child],
      credits: {
        ...base.credits,
        education: [
          { kind: 'school', amount: 2_000_000, label: '첫째' },
          { kind: 'self', amount: 1_000_000, label: '' },
          { kind: 'university', amount: 5_000_000, label: '모르는 사람' },
        ],
      },
    });
    const r = importIndividual(src, 'primary', [], 2025);
    expect(r.added[0]).toMatchObject({ education_kind: 'school', education_amount: 2_000_000 });
    expect(r.person.credits.education).toEqual([
      { kind: 'self', amount: 1_000_000, label: '' },
      { kind: 'university', amount: 5_000_000, label: '모르는 사람' },
    ]);
    expect(r.notes.some((n) => n.includes('교육비 1건은 대상 가족을 알 수 없어'))).toBe(true);
  });

  it('같은 가족의 같은 구분 교육비는 합산한다', () => {
    const base = emptyInput(2025);
    const src = individual({
      dependents: [child],
      credits: {
        ...base.credits,
        education: [
          { kind: 'school', amount: 1_000_000, label: '첫째' },
          { kind: 'school', amount: 500_000, label: '첫째' },
        ],
      },
    });
    expect(importIndividual(src, 'primary', [], 2025).added[0]?.education_amount).toBe(1_500_000);
  });

  it('부양가족이 있으면 의료비를 나눌 수 없다고 안내한다', () => {
    const base = emptyInput(2025);
    const src = individual({
      dependents: [child],
      credits: {
        ...base.credits,
        medical: { general: 1_000_000, specific: 500_000, premature: 0, infertility: 0 },
      },
    });
    const r = importIndividual(src, 'primary', [], 2025);
    expect(r.person.credits.medical.general).toBe(1_000_000);
    expect(r.notes.some((n) => n.includes('의료비 1,500,000원'))).toBe(true);
  });

  it('귀속연도는 맞벌이 계산 연도로 맞추고 다르면 안내한다', () => {
    const r = importIndividual(individual({ tax_year: 2026 }), 'primary', [], 2025);
    expect(r.person.tax_year).toBe(2025);
    expect(r.notes.some((n) => n.includes('2026년 귀속'))).toBe(true);
  });
});
