import type { ReactNode } from 'react';
import {
  Controller,
  get,
  useFormState,
  type Control,
  type FieldError,
  type FieldValues,
  type Path,
} from 'react-hook-form';
import { Field } from './Field';
import { MoneyInput } from './MoneyInput';

type ControlledMoneyFieldProps<T extends FieldValues> = {
  control: Control<T>;
  name: Path<T>;
  label: string;
  hint?: ReactNode;
};

/** 임의의 react-hook-form 폼에서 쓰는 원 단위 금액 필드. */
export function ControlledMoneyField<T extends FieldValues>({
  control,
  name,
  label,
  hint,
}: ControlledMoneyFieldProps<T>) {
  const { errors } = useFormState({ control, name });
  const error = (get(errors, name) as FieldError | undefined)?.message;
  const id = `m-${name.replace(/[.[\]]+/g, '-')}`;
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
