import type { Dependent, EducationExpense, SimulationInput } from '../../api/types';

export function emptyInput(taxYear: number): SimulationInput {
  return {
    tax_year: taxYear,
    income: { annual_earned_income: 0, non_taxable_income: 0 },
    prepaid_tax: { withholding: 0, previous_employer: 0 },
    taxpayer: {
      birth_year: 1990,
      is_female: false,
      is_married: false,
      is_household_head: false,
      disabled: false,
      is_homeless: false,
      marriage_registered_this_year: false,
    },
    dependents: [],
    deductions: {
      national_pension: 0,
      health_insurance: 0,
      employment_insurance: 0,
      housing_rent_loan_repayment: 0,
      long_term_mortgage_interest: 0,
      mortgage_type: null,
      housing_subscription: 0,
      card: {
        credit: 0,
        debit_cash: 0,
        culture: 0,
        sports_facility: 0,
        traditional_market: 0,
        public_transport: 0,
      },
      venture_direct: 0,
      venture_fund: 0,
      national_growth_fund: 0,
    },
    credits: {
      pension_savings: 0,
      irp: 0,
      insurance_general: 0,
      insurance_disabled: 0,
      medical: { general: 0, specific: 0, premature: 0, infertility: 0 },
      education: [],
      donations: {
        political: 0,
        hometown: 0,
        hometown_disaster: 0,
        special: 0,
        general: 0,
        religious: 0,
      },
      monthly_rent: 0,
    },
  };
}

export function newDependent(): Dependent {
  return {
    name: '',
    relation: 'lineal_descendant',
    birth_year: 2015,
    disabled: false,
    income_amount: 0,
    income_is_salary_only: false,
    born_or_adopted_this_year: false,
    child_order: null,
  };
}

export function newEducation(): EducationExpense {
  return { kind: 'school', amount: 0, label: '' };
}

export const RELATION_LABELS: Record<Dependent['relation'], string> = {
  spouse: '배우자',
  lineal_ascendant: '직계존속 (부모·조부모)',
  lineal_descendant: '직계비속 (자녀·손자녀)',
  sibling: '형제자매',
  foster_child: '위탁아동',
};

export const EDUCATION_LABELS: Record<EducationExpense['kind'], string> = {
  self: '본인',
  preschool: '취학전 아동',
  school: '초·중·고',
  university: '대학생',
  disabled_special: '장애인 특수교육비',
};

export const MORTGAGE_LABELS: Record<
  NonNullable<SimulationInput['deductions']['mortgage_type']>,
  string
> = {
  fixed_and_non_deferred_15y: '15년 이상 · 고정금리 + 비거치식',
  fixed_or_non_deferred_15y: '15년 이상 · 고정금리 또는 비거치식',
  other_15y: '15년 이상 · 그 밖의 대출',
  fixed_or_non_deferred_10y: '10년 이상 · 고정금리 또는 비거치식',
};
