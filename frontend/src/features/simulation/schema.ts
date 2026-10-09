/**
 * 입력 폼 검증 스키마 (형식·범위 검증만). 세액은 계산하지 않는다 — 계산은 백엔드 단일 책임.
 * 폼 값 타입은 OpenAPI 생성 타입(SimulationInput)에 할당 가능해야 한다(아래 타입 단언).
 */
import { z } from 'zod';
import type { EducationKind, MortgageType, Relation, SimulationInput } from '../../api/types';

export const MAX_WON = 10_000_000_000_000;

export const RELATIONS = [
  'spouse',
  'lineal_ascendant',
  'lineal_descendant',
  'sibling',
  'foster_child',
] as const satisfies readonly Relation[];

export const EDUCATION_KINDS = [
  'self',
  'preschool',
  'school',
  'university',
  'disabled_special',
] as const satisfies readonly EducationKind[];

export const MORTGAGE_TYPES = [
  'fixed_and_non_deferred_15y',
  'fixed_or_non_deferred_15y',
  'other_15y',
  'fixed_or_non_deferred_10y',
] as const satisfies readonly MortgageType[];

const won = z
  .number({ invalid_type_error: '금액을 입력하세요' })
  .int('원 단위 정수로 입력하세요')
  .min(0, '0원 이상이어야 합니다')
  .max(MAX_WON, '금액이 너무 큽니다');

const birthYear = z
  .number({ invalid_type_error: '출생연도를 입력하세요' })
  .int('연도는 정수로 입력하세요')
  .min(1900, '1900년 이후여야 합니다')
  .max(2100, '2100년 이전이어야 합니다');

const dependentSchema = z.object({
  name: z.string().max(50, '이름은 50자 이내로 입력하세요'),
  relation: z.enum(RELATIONS),
  birth_year: birthYear,
  disabled: z.boolean(),
  income_amount: won,
  income_is_salary_only: z.boolean(),
  born_or_adopted_this_year: z.boolean(),
  child_order: z.number().int().min(1, '1 이상').max(20, '20 이하').nullable().optional(),
});

const educationSchema = z.object({
  kind: z.enum(EDUCATION_KINDS),
  amount: won,
  label: z.string().max(50, '50자 이내로 입력하세요'),
});

export const simulationInputSchema = z
  .object({
    tax_year: z.number().int().min(2000).max(2100),
    income: z.object({ annual_earned_income: won, non_taxable_income: won }),
    prepaid_tax: z.object({ withholding: won, previous_employer: won }),
    taxpayer: z.object({
      birth_year: birthYear,
      is_female: z.boolean(),
      is_married: z.boolean(),
      is_household_head: z.boolean(),
      disabled: z.boolean(),
      is_homeless: z.boolean(),
      marriage_registered_this_year: z.boolean(),
    }),
    dependents: z.array(dependentSchema).max(30, '부양가족은 30명까지 입력할 수 있습니다'),
    deductions: z.object({
      national_pension: won,
      health_insurance: won,
      employment_insurance: won,
      housing_rent_loan_repayment: won,
      long_term_mortgage_interest: won,
      mortgage_type: z.enum(MORTGAGE_TYPES).nullable().optional(),
      housing_subscription: won,
      card: z.object({
        credit: won,
        debit_cash: won,
        culture: won,
        sports_facility: won,
        traditional_market: won,
        public_transport: won,
      }),
      venture_direct: won,
      venture_fund: won,
      national_growth_fund: won,
    }),
    credits: z.object({
      pension_savings: won,
      irp: won,
      insurance_general: won,
      insurance_disabled: won,
      medical: z.object({ general: won, specific: won, premature: won, infertility: won }),
      education: z.array(educationSchema).max(30, '교육비는 30건까지 입력할 수 있습니다'),
      donations: z.object({
        political: won,
        hometown: won,
        hometown_disaster: won,
        special: won,
        general: won,
        religious: won,
      }),
      monthly_rent: won,
    }),
  })
  .strict()
  .superRefine((value, ctx) => {
    if (value.income.non_taxable_income > value.income.annual_earned_income) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['income', 'non_taxable_income'],
        message: '비과세소득은 연간 근로소득을 초과할 수 없습니다',
      });
    }
  });

export type SimulationFormValues = z.infer<typeof simulationInputSchema>;

// 폼 값이 API 입력 타입과 호환되는지 컴파일 타임에 확인한다.
type AssertAssignable<T extends U, U> = T;
export type _FormMatchesApi = AssertAssignable<SimulationFormValues, SimulationInput>;
export type _ApiMatchesForm = AssertAssignable<SimulationInput, SimulationFormValues>;
