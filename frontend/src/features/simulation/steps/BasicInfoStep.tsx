import { useFormContext } from 'react-hook-form';
import { useRuleYears } from '../useRules';
import { CheckboxField, IntegerField, MoneyField, Section } from '../fields';
import type { SimulationFormValues } from '../schema';

export function BasicInfoStep({ hideTaxYear = false }: { hideTaxYear?: boolean }) {
  const { register } = useFormContext<SimulationFormValues>();
  const years = useRuleYears();

  return (
    <div className="step">
      <Section title={hideTaxYear ? '급여' : '귀속연도 · 급여'}>
        <div className="field" hidden={hideTaxYear}>
          <label className="field__label" htmlFor="f-tax_year">
            귀속연도
          </label>
          <select id="f-tax_year" {...register('tax_year', { valueAsNumber: true })}>
            {(years.data?.supported_years ?? [2025]).map((y) => (
              <option key={y} value={y}>
                {y}년 귀속
              </option>
            ))}
          </select>
        </div>
        <MoneyField
          name="income.annual_earned_income"
          label="연간 근로소득 (비과세 포함)"
          hint="예상 연봉·상여 합계 (PC에서는 3000만, 1.5억처럼 입력해도 됩니다)"
        />
        <MoneyField
          name="income.non_taxable_income"
          label="비과세소득"
          hint="식대(월 20만원 한도) 등 비과세 급여"
        />
      </Section>

      <Section title="기납부세액">
        <MoneyField
          name="prepaid_tax.withholding"
          label="현 근무지 원천징수 소득세"
          hint="급여명세서의 소득세 합계 (지방소득세 제외)"
        />
        <MoneyField name="prepaid_tax.previous_employer" label="종전 근무지 결정세액" />
      </Section>

      <Section title="본인 정보">
        <IntegerField name="taxpayer.birth_year" label="출생연도" />
        <CheckboxField name="taxpayer.is_female" label="여성" />
        <CheckboxField name="taxpayer.is_married" label="배우자 있음" />
        <CheckboxField name="taxpayer.is_household_head" label="세대주" />
        <CheckboxField name="taxpayer.disabled" label="장애인" />
        <CheckboxField name="taxpayer.is_homeless" label="무주택 세대주(세대원)" />
        <CheckboxField name="taxpayer.marriage_registered_this_year" label="올해 혼인신고" />
      </Section>
    </div>
  );
}
