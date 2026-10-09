/** 종합소득세 추가 입력(사업·기타소득) 폼 검증 — 형식·범위만. 세액은 백엔드가 계산한다. */
import { z } from 'zod';
import type { GlobalIncomeInput, OtherIncome } from '../../api/types';
import { MAX_WON } from '../simulation/schema';

export const MAX_INCOME_ITEMS = 20;

const won = z
  .number({ invalid_type_error: '금액을 입력하세요' })
  .int('원 단위 정수로 입력하세요')
  .min(0, '0원 이상이어야 합니다')
  .max(MAX_WON, '금액이 너무 큽니다');

export const OTHER_KINDS = [
  'deemed_expense',
  'actual',
] as const satisfies readonly OtherIncome['kind'][];

export const businessIncomeSchema = z.object({
  name: z.string().max(50, '50자 이내로 입력하세요'),
  revenue: won,
  expense_method: z.enum(['book', 'rate']),
  expenses: won,
  expense_rate: z
    .string()
    .regex(/^\d{1,3}(\.\d{1,2})?$/, '경비율은 0~100 사이 숫자로 입력하세요 (소수 둘째 자리까지)')
    .refine((v) => Number(v) <= 100, '경비율은 100%를 넘을 수 없습니다'),
  withholding_tax: won.nullable(),
});

export const otherIncomeSchema = z.object({
  name: z.string().max(50, '50자 이내로 입력하세요'),
  kind: z.enum(OTHER_KINDS),
  revenue: won,
  expenses: won,
  withholding_tax: won.nullable(),
});

export const globalExtraSchema = z.object({
  business_incomes: z.array(businessIncomeSchema).max(MAX_INCOME_ITEMS),
  other_incomes: z.array(otherIncomeSchema).max(MAX_INCOME_ITEMS),
  other_income_taxation: z.enum(['auto', 'comprehensive', 'separate']),
  interim_prepayment: won,
  earned_prepaid_tax: won.nullable(),
});

export type GlobalExtraValues = z.infer<typeof globalExtraSchema>;
export type BusinessIncomeValue = z.infer<typeof businessIncomeSchema>;
export type OtherIncomeValue = z.infer<typeof otherIncomeSchema>;

// 폼 값이 API 입력 타입과 호환되는지 컴파일 타임에 확인한다.
type AssertAssignable<T extends U, U> = T;
export type _ExtraMatchesApi = AssertAssignable<
  GlobalExtraValues,
  Omit<GlobalIncomeInput, 'tax_year' | 'base'>
>;

export function emptyExtra(): GlobalExtraValues {
  return {
    business_incomes: [],
    other_incomes: [],
    other_income_taxation: 'auto',
    interim_prepayment: 0,
    earned_prepaid_tax: null,
  };
}

export function newBusinessIncome(): BusinessIncomeValue {
  return {
    name: '',
    revenue: 0,
    expense_method: 'rate',
    expenses: 0,
    expense_rate: '0',
    withholding_tax: null,
  };
}

export function newOtherIncome(): OtherIncomeValue {
  return { name: '', kind: 'deemed_expense', revenue: 0, expenses: 0, withholding_tax: null };
}

export const OTHER_KIND_LABELS: Record<OtherIncomeValue['kind'], string> = {
  deemed_expense: '강연료·원고료 등 (필요경비 60% 의제)',
  actual: '그 밖의 기타소득 (실제 필요경비)',
};
