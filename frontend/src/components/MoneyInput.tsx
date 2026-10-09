import { useState } from 'react';
import { formatKoreanUnit, formatNumber, parseAmount } from '../lib/format';

type MoneyInputProps = {
  id: string;
  value: number;
  onChange: (value: number) => void;
  onBlur?: () => void;
  name?: string;
  invalid?: boolean;
  placeholder?: string;
  'aria-describedby'?: string;
};

/**
 * 원 단위 금액 입력. 값은 원 단위 정수로 전달하고, 표시만 천 단위 콤마로 포맷한다.
 * "3000만", "1.5억"처럼 만·억 단위 입력도 원으로 변환한다.
 */
export function MoneyInput({
  id,
  value,
  onChange,
  onBlur,
  name,
  invalid,
  placeholder = '0',
  ...rest
}: MoneyInputProps) {
  const [draft, setDraft] = useState<string | null>(null);
  const parseError = draft !== null && parseAmount(draft) === null;
  const text = draft ?? (value ? formatNumber(value) : '');

  const handleBlur = () => {
    if (!parseError) setDraft(null);
    onBlur?.();
  };

  return (
    <div className="money-input">
      <div className="money-input__box">
        <input
          id={id}
          name={name}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          placeholder={placeholder}
          value={text}
          aria-invalid={invalid || parseError || undefined}
          aria-describedby={rest['aria-describedby']}
          onChange={(e) => {
            const next = e.target.value;
            setDraft(next);
            const parsed = parseAmount(next);
            if (parsed !== null) onChange(parsed);
          }}
          onBlur={handleBlur}
        />
        <span className="money-input__suffix">원</span>
      </div>
      {parseError ? (
        <p className="field__error" role="alert">
          금액 형식이 올바르지 않습니다 (예: 1,234,000 / 3000만 / 1.5억)
        </p>
      ) : value >= 10_000 ? (
        <p className="money-input__unit">{formatKoreanUnit(value)}</p>
      ) : null}
    </div>
  );
}
