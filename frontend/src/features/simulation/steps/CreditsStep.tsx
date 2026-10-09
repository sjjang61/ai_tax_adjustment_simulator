import { useFieldArray, useFormContext, useWatch } from 'react-hook-form';
import { formatRate, formatWon } from '../../../lib/format';
import { EDUCATION_LABELS, newEducation } from '../defaults';
import { MoneyField, Section } from '../fields';
import { EDUCATION_KINDS, type SimulationFormValues } from '../schema';
import { useRules } from '../useRules';

export function CreditsStep() {
  const { control, register } = useFormContext<SimulationFormValues>();
  const { fields, append, remove } = useFieldArray({ control, name: 'credits.education' });
  const taxYear = useWatch({ control, name: 'tax_year' });
  const rules = useRules(taxYear).data;
  const pension = rules?.pension_account;
  const medical = rules?.medical_credit;

  return (
    <div className="step">
      <Section
        title="연금계좌"
        note={
          pension
            ? `연금저축 ${formatWon(pension.savings_limit)}, IRP 합산 ${formatWon(pension.combined_limit)} 한도`
            : undefined
        }
      >
        <MoneyField name="credits.pension_savings" label="연금저축 납입액" />
        <MoneyField name="credits.irp" label="퇴직연금(IRP) 납입액" />
      </Section>

      <Section title="보험료">
        <MoneyField
          name="credits.insurance_general"
          label="보장성보험료"
          hint={
            rules
              ? `${formatWon(rules.insurance_credit.general_limit)} 한도 × ${formatRate(rules.insurance_credit.general_rate)}`
              : undefined
          }
        />
        <MoneyField name="credits.insurance_disabled" label="장애인전용 보장성보험료" />
      </Section>

      <Section
        title="의료비"
        note={
          medical
            ? `총급여의 ${formatRate(medical.threshold_rate)}를 초과한 지출분부터 공제됩니다. 실손보험 수령액은 빼고 입력하세요.`
            : undefined
        }
      >
        <MoneyField
          name="credits.medical.specific"
          label="본인·65세 이상·장애인·6세 이하 등"
          hint="한도 없음"
        />
        <MoneyField
          name="credits.medical.general"
          label="그 밖의 부양가족"
          hint={medical ? `연 ${formatWon(medical.general_limit)} 한도` : undefined}
        />
        <MoneyField name="credits.medical.premature" label="미숙아·선천성이상아" />
        <MoneyField name="credits.medical.infertility" label="난임시술비" />
      </Section>

      <fieldset className="section">
        <legend className="section__title">교육비</legend>
        <p className="section__note">교육 대상자 1명당 한 건씩 입력하세요.</p>
        {fields.map((f, index) => (
          <div key={f.id} className="row">
            <div className="field">
              <label className="field__label" htmlFor={`f-education-${index}-kind`}>
                구분
              </label>
              <select
                id={`f-education-${index}-kind`}
                {...register(`credits.education.${index}.kind`)}
              >
                {EDUCATION_KINDS.map((k) => (
                  <option key={k} value={k}>
                    {EDUCATION_LABELS[k]}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor={`f-education-${index}-label`}>
                대상자(선택)
              </label>
              <input
                id={`f-education-${index}-label`}
                {...register(`credits.education.${index}.label`)}
              />
            </div>
            <MoneyField name={`credits.education.${index}.amount`} label="교육비" />
            <button
              type="button"
              className="btn btn--ghost btn--small"
              onClick={() => remove(index)}
              aria-label={`교육비 ${index + 1} 삭제`}
            >
              삭제
            </button>
          </div>
        ))}
        <button type="button" className="btn btn--secondary" onClick={() => append(newEducation())}>
          + 교육비 추가
        </button>
      </fieldset>

      <Section title="기부금">
        <MoneyField name="credits.donations.political" label="정치자금기부금" />
        <MoneyField
          name="credits.donations.hometown"
          label="고향사랑기부금"
          hint={
            rules ? `연 ${formatWon(rules.donation_credit.hometown_annual_limit)} 한도` : undefined
          }
        />
        <MoneyField
          name="credits.donations.hometown_disaster"
          label="고향사랑기부금 (특별재난지역)"
        />
        <MoneyField name="credits.donations.special" label="특례기부금" />
        <MoneyField name="credits.donations.general" label="일반기부금 (종교단체 외)" />
        <MoneyField name="credits.donations.religious" label="일반기부금 (종교단체)" />
      </Section>

      <Section title="월세">
        <MoneyField
          name="credits.monthly_rent"
          label="월세 지급액 (연간)"
          hint={
            rules
              ? `총급여 ${formatWon(rules.rent_credit.gross_salary_limit)} 이하 무주택 세대주, 연 ${formatWon(rules.rent_credit.payment_limit)} 한도`
              : undefined
          }
        />
      </Section>
    </div>
  );
}
