/** 맞벌이 공유 부양가족 폼 검증 (형식·범위만). 타입은 OpenAPI 생성 타입과 호환되어야 한다. */
import { z } from 'zod';
import type { SharedDependent, Spouse } from '../../api/types';
import { MAX_WON } from '../simulation/schema';

export const MAX_SHARED_DEPENDENTS = 10;

export const SPOUSE_LABELS: Record<Spouse, string> = { primary: '본인', spouse: '배우자' };

const won = z
  .number({ invalid_type_error: '금액을 입력하세요' })
  .int('원 단위 정수로 입력하세요')
  .min(0, '0원 이상이어야 합니다')
  .max(MAX_WON, '금액이 너무 큽니다');

export const SHARED_RELATIONS = [
  'lineal_ascendant',
  'lineal_descendant',
  'sibling',
  'foster_child',
] as const satisfies readonly SharedDependent['relation'][];

export const SHARED_EDUCATION_KINDS = [
  'preschool',
  'school',
  'university',
  'disabled_special',
] as const satisfies readonly NonNullable<SharedDependent['education_kind']>[];

export const sharedDependentSchema = z.object({
  name: z.string().max(50, '이름은 50자 이내로 입력하세요'),
  relation: z.enum(SHARED_RELATIONS),
  birth_year: z
    .number({ invalid_type_error: '출생연도를 입력하세요' })
    .int()
    .min(1900, '1900년 이후여야 합니다')
    .max(2100, '2100년 이전이어야 합니다'),
  disabled: z.boolean(),
  income_amount: won,
  income_is_salary_only: z.boolean(),
  born_or_adopted_this_year: z.boolean(),
  child_order: z.number().int().min(1).max(20).nullable().optional(),
  medical_expense: won,
  education_kind: z.enum(SHARED_EDUCATION_KINDS).nullable().optional(),
  education_amount: won,
  assigned_to: z.enum(['primary', 'spouse']),
});

export const sharedFormSchema = z.object({
  shared_dependents: z
    .array(sharedDependentSchema)
    .max(MAX_SHARED_DEPENDENTS, `부양가족은 ${MAX_SHARED_DEPENDENTS}명까지 입력할 수 있습니다`),
});

export type SharedFormValues = z.infer<typeof sharedFormSchema>;
export type SharedDependentFormValue = z.infer<typeof sharedDependentSchema>;

// 폼 값이 API 타입에 할당 가능한지 컴파일 타임 확인 (배우자·본인 교육비는 폼에서 제외)
type AssertAssignable<T extends U, U> = T;
export type _SharedMatchesApi = AssertAssignable<SharedDependentFormValue, SharedDependent>;

export function newSharedDependent(): SharedDependentFormValue {
  return {
    name: '',
    relation: 'lineal_descendant',
    birth_year: 2015,
    disabled: false,
    income_amount: 0,
    income_is_salary_only: false,
    born_or_adopted_this_year: false,
    child_order: null,
    medical_expense: 0,
    education_kind: null,
    education_amount: 0,
    assigned_to: 'primary',
  };
}
