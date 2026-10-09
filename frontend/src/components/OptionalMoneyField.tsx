import {
  useWatch,
  type Control,
  type FieldValues,
  type Path,
  type PathValue,
  type UseFormSetValue,
} from 'react-hook-form';
import { ControlledMoneyField } from './ControlledMoneyField';

type OptionalMoneyFieldProps<T extends FieldValues> = {
  control: Control<T>;
  setValue: UseFormSetValue<T>;
  name: Path<T>;
  autoHint: string;
  toggleLabel?: string;
  fieldLabel?: string;
};

/** 직접 입력 토글 금액: 체크하지 않으면 null(백엔드가 규칙에 따라 추정·계산)로 보낸다. */
export function OptionalMoneyField<T extends FieldValues>({
  control,
  setValue,
  name,
  autoHint,
  toggleLabel = '원천징수세액 직접 입력',
  fieldLabel = '원천징수된 소득세',
}: OptionalMoneyFieldProps<T>) {
  const value = useWatch({ control, name });
  const manual = value !== null && value !== undefined;
  const id = `w-${name.replace(/[.[\]]+/g, '-')}`;
  return (
    <div className="withholding">
      <div className="checkbox">
        <input
          id={id}
          type="checkbox"
          checked={manual}
          onChange={(e) =>
            setValue(name, (e.target.checked ? 0 : null) as PathValue<T, Path<T>>, {
              shouldDirty: true,
            })
          }
        />
        <label htmlFor={id}>{toggleLabel}</label>
      </div>
      {manual ? (
        <ControlledMoneyField control={control} name={name} label={fieldLabel} />
      ) : (
        <p className="field__hint">{autoHint}</p>
      )}
    </div>
  );
}
