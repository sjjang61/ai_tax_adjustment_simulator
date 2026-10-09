import { useFieldArray, useFormContext, useWatch } from 'react-hook-form';
import { ControlledMoneyField } from '../../components/ControlledMoneyField';
import { OptionalMoneyField } from '../../components/OptionalMoneyField';
import { Field } from '../../components/Field';
import { formatRate, formatWon } from '../../lib/format';
import { Section } from '../simulation/fields';
import { useRules } from '../simulation/useRules';
import { BusinessImportPanel } from './BusinessImportPanel';
import {
  MAX_INCOME_ITEMS,
  OTHER_KINDS,
  OTHER_KIND_LABELS,
  newBusinessIncome,
  newOtherIncome,
  type GlobalExtraValues,
} from './schema';

export function IncomeItemsStep({ taxYear }: { taxYear: number }) {
  const { control, register, formState, setValue } = useFormContext<GlobalExtraValues>();
  const business = useFieldArray({ control, name: 'business_incomes' });
  const others = useFieldArray({ control, name: 'other_incomes' });
  const businessValues = useWatch({ control, name: 'business_incomes' });
  const rules = useRules(taxYear).data?.global_income;
  // 세율은 귀속연도 규칙에서 가져온다 (로딩 전에는 일반 문구)
  const businessRate = rules ? formatRate(rules.business_withholding_rate) : '원천징수세율';
  const otherRate = rules ? formatRate(rules.other_withholding_rate) : '원천징수세율';

  return (
    <div className="step">
      <p className="step__intro">
        근로소득 외에 올해 받은 사업소득(프리랜서·인적용역 등)과 기타소득(강연료·원고료 등)을
        추가하세요. 없으면 비워 두고 다음으로 넘어가면 됩니다.
      </p>

      <BusinessImportPanel
        taxYear={taxYear}
        onImport={(share) =>
          business.append({
            name: share.business_income.name,
            revenue: share.business_income.revenue,
            expense_method: 'book',
            expenses: share.business_income.expenses,
            expense_rate: '0',
            withholding_tax: share.business_income.withholding_tax ?? null,
          })
        }
      />

      <fieldset className="section">
        <legend className="section__title">사업소득 ({business.fields.length}건)</legend>
        {business.fields.length === 0 ? <p className="empty">추가한 사업소득이 없습니다.</p> : null}
        {business.fields.map((f, i) => {
          const method = businessValues?.[i]?.expense_method;
          const rateError = formState.errors.business_incomes?.[i]?.expense_rate?.message;
          return (
            <div key={f.id} className="income-item">
              <div className="income-item__head">
                <strong>사업소득 {i + 1}</strong>
                <button
                  type="button"
                  className="btn btn--ghost btn--small"
                  onClick={() => business.remove(i)}
                  aria-label={`사업소득 ${i + 1} 삭제`}
                >
                  삭제
                </button>
              </div>
              <div className="section__grid">
                <div className="field">
                  <label className="field__label" htmlFor={`b-${i}-name`}>
                    이름(선택)
                  </label>
                  <input
                    id={`b-${i}-name`}
                    placeholder="예: 프리랜서 개발"
                    {...register(`business_incomes.${i}.name`)}
                  />
                </div>
                <ControlledMoneyField
                  control={control}
                  name={`business_incomes.${i}.revenue`}
                  label="총수입금액"
                />
                <div className="field">
                  <label className="field__label" htmlFor={`b-${i}-method`}>
                    필요경비 계산 방법
                  </label>
                  <select
                    id={`b-${i}-method`}
                    {...register(`business_incomes.${i}.expense_method`)}
                  >
                    <option value="rate">경비율 (단순·기준경비율)</option>
                    <option value="book">장부 (실제 경비)</option>
                  </select>
                </div>
                {method === 'book' ? (
                  <ControlledMoneyField
                    control={control}
                    name={`business_incomes.${i}.expenses`}
                    label="필요경비"
                  />
                ) : (
                  <Field
                    id={`b-${i}-rate`}
                    label="경비율 (%)"
                    hint="홈택스 「기준·단순경비율 조회」에서 업종코드로 확인하세요"
                    error={rateError}
                  >
                    <input
                      id={`b-${i}-rate`}
                      inputMode="decimal"
                      aria-invalid={Boolean(rateError) || undefined}
                      {...register(`business_incomes.${i}.expense_rate`)}
                    />
                  </Field>
                )}
              </div>
              <OptionalMoneyField
                control={control}
                setValue={setValue}
                name={`business_incomes.${i}.withholding_tax`}
                autoHint={`비워 두면 총수입금액 × ${businessRate}가 원천징수된 것으로 계산합니다.`}
              />
            </div>
          );
        })}
        <button
          type="button"
          className="btn btn--secondary"
          disabled={business.fields.length >= MAX_INCOME_ITEMS}
          onClick={() => business.append(newBusinessIncome())}
        >
          + 사업소득 추가
        </button>
      </fieldset>

      <fieldset className="section">
        <legend className="section__title">기타소득 ({others.fields.length}건)</legend>
        {others.fields.length === 0 ? <p className="empty">추가한 기타소득이 없습니다.</p> : null}
        {others.fields.map((f, i) => (
          <div key={f.id} className="income-item">
            <div className="income-item__head">
              <strong>기타소득 {i + 1}</strong>
              <button
                type="button"
                className="btn btn--ghost btn--small"
                onClick={() => others.remove(i)}
                aria-label={`기타소득 ${i + 1} 삭제`}
              >
                삭제
              </button>
            </div>
            <div className="section__grid">
              <div className="field">
                <label className="field__label" htmlFor={`o-${i}-name`}>
                  이름(선택)
                </label>
                <input
                  id={`o-${i}-name`}
                  placeholder="예: 원고료"
                  {...register(`other_incomes.${i}.name`)}
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor={`o-${i}-kind`}>
                  종류
                </label>
                <select id={`o-${i}-kind`} {...register(`other_incomes.${i}.kind`)}>
                  {OTHER_KINDS.map((k) => (
                    <option key={k} value={k}>
                      {OTHER_KIND_LABELS[k]}
                    </option>
                  ))}
                </select>
              </div>
              <ControlledMoneyField
                control={control}
                name={`other_incomes.${i}.revenue`}
                label="지급받은 금액 (총수입금액)"
              />
              <ControlledMoneyField
                control={control}
                name={`other_incomes.${i}.expenses`}
                label="실제 필요경비"
                hint="60% 의제 항목은 의제 금액과 실제 경비 중 큰 금액을 적용합니다"
              />
            </div>
            <OptionalMoneyField
              control={control}
              setValue={setValue}
              name={`other_incomes.${i}.withholding_tax`}
              autoHint={`비워 두면 기타소득금액 × ${otherRate}가 원천징수된 것으로 계산합니다.`}
            />
          </div>
        ))}
        <button
          type="button"
          className="btn btn--secondary"
          disabled={others.fields.length >= MAX_INCOME_ITEMS}
          onClick={() => others.append(newOtherIncome())}
        >
          + 기타소득 추가
        </button>
      </fieldset>

      <Section title="과세 방법 · 기납부세액">
        <div className="field">
          <label className="field__label" htmlFor="g-taxation">
            기타소득 과세 방법
          </label>
          <select id="g-taxation" {...register('other_income_taxation')}>
            <option value="auto">유리한 쪽 자동 선택</option>
            <option value="comprehensive">종합과세</option>
            <option value="separate">분리과세</option>
          </select>
          <p className="field__hint">
            {rules
              ? `기타소득금액 합계가 ${formatWon(rules.other_separate_threshold)} 이하일 때만 분리과세를 선택할 수 있습니다.`
              : '기타소득금액이 기준 금액 이하일 때만 분리과세를 선택할 수 있습니다.'}
          </p>
        </div>
        <OptionalMoneyField
          control={control}
          setValue={setValue}
          name="earned_prepaid_tax"
          toggleLabel="근로소득 기납부세액 직접 입력"
          fieldLabel="근로소득 기납부세액"
          autoHint="비워 두면 연말정산 결정세액(근로소득원천징수영수증의 결정세액)으로 계산합니다."
        />
        <ControlledMoneyField
          control={control}
          name="interim_prepayment"
          label="중간예납세액"
          hint="11월에 고지·납부한 중간예납 소득세"
        />
      </Section>
    </div>
  );
}
