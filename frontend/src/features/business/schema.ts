/** 사업자 소득관리 폼 검증 (형식·범위만). 배분 계산은 백엔드가 한다. */
import { z } from 'zod';
import type { BusinessRecord, StoredBusinessRecord } from '../../api/types';
import { MAX_WON } from '../simulation/schema';

export const MAX_PARTNERS = 10;

const won = z
  .number({ invalid_type_error: '금액을 입력하세요' })
  .int('원 단위 정수로 입력하세요')
  .min(0, '0원 이상이어야 합니다')
  .max(MAX_WON, '금액이 너무 큽니다');

export const partnerSchema = z.object({
  name: z.string().min(1, '대표자 이름을 입력하세요').max(50, '50자 이내로 입력하세요'),
  share: z
    .number({ invalid_type_error: '지분을 입력하세요' })
    .int('정수로 입력하세요')
    .min(1, '지분은 1 이상이어야 합니다')
    .max(1_000_000),
  simulation_id: z.number().int().nullable(),
});

export const businessFormSchema = z
  .object({
    name: z.string().min(1, '사업장 이름을 입력하세요').max(50, '50자 이내로 입력하세요'),
    tax_year: z.number().int().min(2000).max(2100),
    revenue: won,
    expense_method: z.enum(['book', 'rate']),
    expenses: won,
    expense_rate: z
      .string()
      .regex(/^\d{1,3}(\.\d{1,2})?$/, '경비율은 0~100 사이 숫자로 입력하세요 (소수 둘째 자리까지)')
      .refine((v) => Number(v) <= 100, '경비율은 100%를 넘을 수 없습니다'),
    withholding_tax: won.nullable(),
    partners: z
      .array(partnerSchema)
      .min(1, '대표자를 1명 이상 입력하세요')
      .max(MAX_PARTNERS, `대표자는 ${MAX_PARTNERS}명까지 입력할 수 있습니다`),
  })
  .superRefine((v, ctx) => {
    const seen = new Set<number>();
    v.partners.forEach((p, i) => {
      if (p.simulation_id == null) return;
      if (seen.has(p.simulation_id)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['partners', i, 'simulation_id'],
          message: '같은 연말정산 결과를 여러 대표에 연결할 수 없습니다',
        });
      }
      seen.add(p.simulation_id);
    });
  });

export type BusinessFormValues = z.infer<typeof businessFormSchema>;

type AssertAssignable<T extends U, U> = T;
export type _BusinessMatchesApi = AssertAssignable<BusinessFormValues, BusinessRecord>;

export function emptyBusiness(taxYear: number): BusinessFormValues {
  return {
    name: '',
    tax_year: taxYear,
    revenue: 0,
    expense_method: 'book',
    expenses: 0,
    expense_rate: '0',
    withholding_tax: null,
    partners: [
      { name: '', share: 5, simulation_id: null },
      { name: '', share: 5, simulation_id: null },
    ],
  };
}

export function toBusinessForm(record: StoredBusinessRecord): BusinessFormValues {
  return {
    name: record.name,
    tax_year: record.tax_year,
    revenue: record.revenue,
    expense_method: record.expense_method,
    expenses: record.expenses,
    expense_rate: String(Number(record.expense_rate)),
    withholding_tax: record.withholding_tax ?? null,
    partners: record.partners.map((p) => ({
      name: p.name,
      share: p.share,
      simulation_id: p.simulation_id ?? null,
    })),
  };
}
