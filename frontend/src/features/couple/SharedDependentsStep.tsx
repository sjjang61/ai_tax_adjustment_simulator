import {
  Controller,
  useFieldArray,
  useFormContext,
  useWatch,
  type FieldPath,
} from 'react-hook-form';
import { Field } from '../../components/Field';
import { MoneyInput } from '../../components/MoneyInput';
import { EDUCATION_LABELS, RELATION_LABELS } from '../simulation/defaults';
import { useRules } from '../simulation/useRules';
import {
  MAX_SHARED_DEPENDENTS,
  SHARED_EDUCATION_KINDS,
  SHARED_RELATIONS,
  newSharedDependent,
  type SharedFormValues,
} from './schema';

type Path = FieldPath<SharedFormValues>;

function SharedMoneyField({ name, label, hint }: { name: Path; label: string; hint?: string }) {
  const { control, getFieldState, formState } = useFormContext<SharedFormValues>();
  const id = `c-${name.replace(/\./g, '-')}`;
  const error = getFieldState(name, formState).error?.message;
  return (
    <Field id={id} label={label} hint={hint} error={error}>
      <Controller
        control={control}
        name={name}
        render={({ field }) => (
          <MoneyInput
            id={id}
            name={field.name}
            value={typeof field.value === 'number' ? field.value : 0}
            onChange={field.onChange}
            onBlur={field.onBlur}
            invalid={Boolean(error)}
          />
        )}
      />
    </Field>
  );
}

/** 맞벌이: 부부 중 누가 공제받을지 정할 부양가족과 그 가족의 의료비·교육비. */
export function SharedDependentsStep({ taxYear }: { taxYear: number }) {
  const { control, register, getFieldState, formState } = useFormContext<SharedFormValues>();
  const medical = useRules(taxYear).data?.medical_credit;
  const { fields, append, remove } = useFieldArray({ control, name: 'shared_dependents' });
  const values = useWatch({ control, name: 'shared_dependents' });

  return (
    <div className="step">
      <p className="step__intro">
        자녀·부모님 등 부부가 함께 부양하는 가족을 입력하세요. 부양가족 한 명은 부부 중 한 사람만
        공제받을 수 있고, 그 가족의 의료비·교육비와 자녀세액공제도 공제받는 사람에게 함께 갑니다.
        결과 단계에서 가능한 모든 배분을 계산해 가장 유리한 쪽을 추천합니다.
      </p>
      {fields.length === 0 ? <p className="empty">입력한 부양가족이 없습니다.</p> : null}

      {fields.map((f, index) => {
        const p = `shared_dependents.${index}` as const;
        const birthError = getFieldState(`${p}.birth_year`, formState).error?.message;
        const born = values?.[index]?.born_or_adopted_this_year;
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
                <label className="field__label" htmlFor={`c-${index}-name`}>
                  이름(선택)
                </label>
                <input id={`c-${index}-name`} {...register(`${p}.name`)} />
              </div>
              <div className="field">
                <label className="field__label" htmlFor={`c-${index}-relation`}>
                  관계
                </label>
                <select id={`c-${index}-relation`} {...register(`${p}.relation`)}>
                  {SHARED_RELATIONS.map((r) => (
                    <option key={r} value={r}>
                      {RELATION_LABELS[r]}
                    </option>
                  ))}
                </select>
              </div>
              <Field id={`c-${index}-birth`} label="출생연도" error={birthError}>
                <input
                  id={`c-${index}-birth`}
                  type="number"
                  inputMode="numeric"
                  aria-invalid={Boolean(birthError) || undefined}
                  {...register(`${p}.birth_year`, {
                    setValueAs: (v: unknown) => (v === '' || v == null ? Number.NaN : Number(v)),
                  })}
                />
              </Field>
              <SharedMoneyField
                name={`${p}.income_amount`}
                label="연간 소득금액"
                hint="근로소득만 있으면 총급여를 입력하고 아래를 체크하세요"
              />
              <div className="checkbox">
                <input
                  id={`c-${index}-salary-only`}
                  type="checkbox"
                  {...register(`${p}.income_is_salary_only`)}
                />
                <label htmlFor={`c-${index}-salary-only`}>근로소득만 있음</label>
              </div>
              <div className="checkbox">
                <input id={`c-${index}-disabled`} type="checkbox" {...register(`${p}.disabled`)} />
                <label htmlFor={`c-${index}-disabled`}>장애인</label>
              </div>
              <div className="checkbox">
                <input
                  id={`c-${index}-born`}
                  type="checkbox"
                  {...register(`${p}.born_or_adopted_this_year`)}
                />
                <label htmlFor={`c-${index}-born`}>올해 출생·입양</label>
              </div>
              {born ? (
                <div className="field">
                  <label className="field__label" htmlFor={`c-${index}-order`}>
                    몇째 자녀인가요?
                  </label>
                  <input
                    id={`c-${index}-order`}
                    type="number"
                    {...register(`${p}.child_order`, {
                      setValueAs: (v: unknown) => (v === '' || v == null ? null : Number(v)),
                    })}
                  />
                </div>
              ) : null}
              <SharedMoneyField
                name={`${p}.medical_expense`}
                label="이 가족의 의료비"
                hint={
                  medical
                    ? `${medical.specific_min_age}세 이상·${medical.specific_max_age_at_start}세 이하(1월 1일 기준)·장애인은 한도 없는 의료비로 자동 분류됩니다`
                    : undefined
                }
              />
              <div className="field">
                <label className="field__label" htmlFor={`c-${index}-edu-kind`}>
                  교육비 구분
                </label>
                <select
                  id={`c-${index}-edu-kind`}
                  {...register(`${p}.education_kind`, {
                    setValueAs: (v: unknown) => (v === '' || v == null ? null : v),
                  })}
                >
                  <option value="">없음</option>
                  {SHARED_EDUCATION_KINDS.map((k) => (
                    <option key={k} value={k}>
                      {EDUCATION_LABELS[k]}
                    </option>
                  ))}
                </select>
              </div>
              <SharedMoneyField name={`${p}.education_amount`} label="이 가족의 교육비" />
              <div className="field">
                <label className="field__label" htmlFor={`c-${index}-assigned`}>
                  현재 공제받을 예정인 사람
                </label>
                <select id={`c-${index}-assigned`} {...register(`${p}.assigned_to`)}>
                  <option value="primary">본인</option>
                  <option value="spouse">배우자</option>
                </select>
              </div>
            </div>
          </fieldset>
        );
      })}

      <button
        type="button"
        className="btn btn--secondary"
        disabled={fields.length >= MAX_SHARED_DEPENDENTS}
        onClick={() => append(newSharedDependent())}
      >
        + 부양가족 추가
      </button>
      {fields.length >= MAX_SHARED_DEPENDENTS ? (
        <p className="field__hint">부양가족은 {MAX_SHARED_DEPENDENTS}명까지 입력할 수 있습니다.</p>
      ) : null}
    </div>
  );
}
