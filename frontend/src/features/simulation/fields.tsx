import type { ReactNode } from 'react';
import { Controller, get, useFormContext, type FieldPath, type FieldError } from 'react-hook-form';
import { Field } from '../../components/Field';
import { MoneyInput } from '../../components/MoneyInput';
import type { SimulationFormValues } from './schema';

type Path = FieldPath<SimulationFormValues>;

function fieldId(name: string): string {
  return `f-${name.replace(/[.[\]]+/g, '-')}`;
}

function useFieldError(name: Path): string | undefined {
  const {
    formState: { errors },
  } = useFormContext<SimulationFormValues>();
  return (get(errors, name) as FieldError | undefined)?.message;
}

/** 원 단위 금액 필드 (react-hook-form Controller + MoneyInput). */
export function MoneyField({ name, label, hint }: { name: Path; label: string; hint?: ReactNode }) {
  const { control } = useFormContext<SimulationFormValues>();
  const error = useFieldError(name);
  const id = fieldId(name);
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
            aria-describedby={hint ? `${id}-hint` : undefined}
          />
        )}
      />
    </Field>
  );
}

/** 정수 필드 (출생연도 등). 빈 값은 nullable이면 null, 아니면 NaN → zod에서 오류 처리. */
export function IntegerField({
  name,
  label,
  hint,
  nullable = false,
}: {
  name: Path;
  label: string;
  hint?: ReactNode;
  nullable?: boolean;
}) {
  const { register } = useFormContext<SimulationFormValues>();
  const error = useFieldError(name);
  const id = fieldId(name);
  return (
    <Field id={id} label={label} hint={hint} error={error}>
      <input
        id={id}
        type="number"
        inputMode="numeric"
        aria-invalid={Boolean(error) || undefined}
        {...register(name, {
          setValueAs: (v: unknown) =>
            v === '' || v === null || v === undefined ? (nullable ? null : Number.NaN) : Number(v),
        })}
      />
    </Field>
  );
}

export function CheckboxField({ name, label }: { name: Path; label: string }) {
  const { register } = useFormContext<SimulationFormValues>();
  const id = fieldId(name);
  return (
    <div className="checkbox">
      <input id={id} type="checkbox" {...register(name)} />
      <label htmlFor={id}>{label}</label>
    </div>
  );
}

export function Section({
  title,
  children,
  note,
}: {
  title: string;
  children: ReactNode;
  note?: ReactNode;
}) {
  return (
    <fieldset className="section">
      <legend className="section__title">{title}</legend>
      {note ? <p className="section__note">{note}</p> : null}
      <div className="section__grid">{children}</div>
    </fieldset>
  );
}
