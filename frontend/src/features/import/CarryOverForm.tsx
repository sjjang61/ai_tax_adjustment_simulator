import { useState } from 'react';

type CarryOverFormProps = {
  sourceYear: number;
  supportedYears: readonly number[];
  pending: boolean;
  onSubmit: (targetYear: number, salaryIncreaseRate: number | undefined) => void;
  onCancel: () => void;
};

/** 작년 데이터를 올해 초안으로 이월할 때의 대상 연도·급여 인상률 입력. */
export function CarryOverForm({
  sourceYear,
  supportedYears,
  pending,
  onSubmit,
  onCancel,
}: CarryOverFormProps) {
  const candidates = supportedYears.filter((y) => y > sourceYear);
  const [targetYear, setTargetYear] = useState<number | undefined>(candidates[0]);
  const [rate, setRate] = useState('');
  const rateNumber = rate.trim() === '' ? undefined : Number(rate);
  const rateInvalid =
    rateNumber !== undefined &&
    (!Number.isFinite(rateNumber) || rateNumber < -50 || rateNumber > 100);

  if (candidates.length === 0) {
    return (
      <div className="carry-over">
        <p>이월할 수 있는 이후 귀속연도가 없습니다.</p>
        <button type="button" className="btn btn--ghost btn--small" onClick={onCancel}>
          닫기
        </button>
      </div>
    );
  }

  return (
    <form
      className="carry-over"
      aria-label="올해로 이월"
      onSubmit={(e) => {
        e.preventDefault();
        if (targetYear !== undefined && !rateInvalid) onSubmit(targetYear, rateNumber);
      }}
    >
      <label>
        대상 연도
        <select value={targetYear} onChange={(e) => setTargetYear(Number(e.target.value))}>
          {candidates.map((y) => (
            <option key={y} value={y}>
              {y}년 귀속
            </option>
          ))}
        </select>
      </label>
      <label>
        급여 인상률(%)
        <input
          type="number"
          step="0.1"
          placeholder="예: 3.5"
          value={rate}
          aria-invalid={rateInvalid || undefined}
          onChange={(e) => setRate(e.target.value)}
        />
      </label>
      {rateInvalid ? (
        <p className="field__error" role="alert">
          인상률은 -50% ~ 100% 사이로 입력하세요
        </p>
      ) : null}
      <button
        type="submit"
        className="btn btn--primary btn--small"
        disabled={pending || rateInvalid}
      >
        초안 만들기
      </button>
      <button type="button" className="btn btn--ghost btn--small" onClick={onCancel}>
        취소
      </button>
    </form>
  );
}
