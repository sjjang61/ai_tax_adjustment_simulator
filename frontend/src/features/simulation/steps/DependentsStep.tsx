import { useFieldArray, useFormContext, useWatch } from 'react-hook-form';
import { RELATION_LABELS, newDependent } from '../defaults';
import { CheckboxField, IntegerField, MoneyField } from '../fields';
import { RELATIONS, type SimulationFormValues } from '../schema';
import { useRules } from '../useRules';
import { formatWon } from '../../../lib/format';

export function DependentsStep() {
  const { control, register } = useFormContext<SimulationFormValues>();
  const { fields, append, remove } = useFieldArray({ control, name: 'dependents' });
  const taxYear = useWatch({ control, name: 'tax_year' });
  const dependents = useWatch({ control, name: 'dependents' });
  const rules = useRules(taxYear).data;

  return (
    <div className="step">
      <p className="step__intro">
        본인은 자동으로 기본공제됩니다. 배우자·자녀·부모 등 부양가족을 추가하세요.
        {rules ? (
          <>
            {' '}
            기본공제 1인당 {formatWon(rules.personal.basic_per_person)}, 소득금액{' '}
            {formatWon(rules.personal.dependent_income_limit)} 이하(근로소득만 있으면 총급여{' '}
            {formatWon(rules.personal.dependent_salary_only_limit)} 이하) 요건이 있습니다.
          </>
        ) : null}
      </p>

      {fields.length === 0 ? <p className="empty">등록된 부양가족이 없습니다.</p> : null}

      {fields.map((f, index) => {
        const born = dependents?.[index]?.born_or_adopted_this_year;
        return (
          <fieldset key={f.id} className="section card-item">
            <legend className="section__title">
              부양가족 {index + 1}
              <button
                type="button"
                className="btn btn--ghost btn--small"
                onClick={() => remove(index)}
                aria-label={`부양가족 ${index + 1} 삭제`}
              >
                삭제
              </button>
            </legend>
            <div className="section__grid">
              <div className="field">
                <label className="field__label" htmlFor={`f-dependents-${index}-name`}>
                  이름(선택)
                </label>
                <input
                  id={`f-dependents-${index}-name`}
                  {...register(`dependents.${index}.name`)}
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor={`f-dependents-${index}-relation`}>
                  관계
                </label>
                <select
                  id={`f-dependents-${index}-relation`}
                  {...register(`dependents.${index}.relation`)}
                >
                  {RELATIONS.map((r) => (
                    <option key={r} value={r}>
                      {RELATION_LABELS[r]}
                    </option>
                  ))}
                </select>
              </div>
              <IntegerField name={`dependents.${index}.birth_year`} label="출생연도" />
              <MoneyField
                name={`dependents.${index}.income_amount`}
                label="연간 소득금액"
                hint="근로소득만 있으면 총급여를 입력하고 아래를 체크하세요"
              />
              <CheckboxField
                name={`dependents.${index}.income_is_salary_only`}
                label="근로소득만 있음"
              />
              <CheckboxField name={`dependents.${index}.disabled`} label="장애인" />
              <CheckboxField
                name={`dependents.${index}.born_or_adopted_this_year`}
                label="올해 출생·입양"
              />
              {born ? (
                <IntegerField
                  name={`dependents.${index}.child_order`}
                  label="몇째 자녀인가요?"
                  nullable
                />
              ) : null}
            </div>
          </fieldset>
        );
      })}

      <button type="button" className="btn btn--secondary" onClick={() => append(newDependent())}>
        + 부양가족 추가
      </button>
    </div>
  );
}
