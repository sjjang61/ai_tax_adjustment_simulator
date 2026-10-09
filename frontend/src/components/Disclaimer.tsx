export const DISCLAIMER_TEXT =
  '이 결과는 참고용 시뮬레이션이며 실제 연말정산 결과와 다를 수 있습니다. 정확한 금액은 국세청 홈택스 연말정산 간소화 서비스 및 회사 정산 결과를 확인하세요.';

/** 결과 화면에 항상 표시하는 고지. */
export function Disclaimer({ text = DISCLAIMER_TEXT }: { text?: string }) {
  return (
    <p className="disclaimer" role="note">
      <span className="disclaimer__icon" aria-hidden="true">
        ⓘ
      </span>
      {text}
    </p>
  );
}
