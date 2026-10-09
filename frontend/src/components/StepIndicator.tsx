type StepIndicatorProps = {
  steps: readonly string[];
  current: number;
  /** 단계를 누르면 해당 단계로 바로 이동한다. 없으면 표시 전용. */
  onSelect?: (index: number) => void;
};

type StepState = 'done' | 'current' | 'todo';

const STATE_SUFFIX: Record<StepState, string> = {
  done: ' (완료)',
  current: ' (현재 단계)',
  todo: '',
};

/** 프로세스(스테퍼) 형태의 단계 표시. 모든 단계를 눌러 바로 이동할 수 있다. */
export function StepIndicator({ steps, current, onSelect }: StepIndicatorProps) {
  // 연결선 채움 비율: 0(첫 단계) ~ 1(마지막 단계)
  const ratio = steps.length > 1 ? current / (steps.length - 1) : 1;
  return (
    <nav className="stepper" aria-label="입력 단계">
      <p className="stepper__progress">
        <span>
          {current + 1} / {steps.length} 단계
        </span>
        <span className="stepper__current-label">{steps[current]}</span>
      </p>
      <ol className="stepper__list" style={{ ['--stepper-ratio' as string]: ratio }}>
        {steps.map((label, index) => {
          const state: StepState =
            index === current ? 'current' : index < current ? 'done' : 'todo';
          return (
            <li key={label} className={`stepper__item stepper__item--${state}`} data-state={state}>
              <button
                type="button"
                className="stepper__button"
                aria-current={state === 'current' ? 'step' : undefined}
                aria-label={`${index + 1}단계 ${label}${STATE_SUFFIX[state]}`}
                disabled={!onSelect}
                onClick={() => {
                  if (index !== current) onSelect?.(index);
                }}
              >
                <span className="stepper__dot" aria-hidden="true">
                  {state === 'done' ? '✓' : index + 1}
                </span>
                <span className="stepper__label" aria-hidden="true">
                  {label}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
