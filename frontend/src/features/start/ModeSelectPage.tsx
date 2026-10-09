import { Link } from 'react-router-dom';

const HOW_IT_WORKS = [
  { title: '급여 입력', desc: '연봉, 비과세, 이미 낸 세금(원천징수액)' },
  { title: '공제 입력', desc: '부양가족, 카드, 연금, 의료비·교육비 등' },
  { title: '결과 확인', desc: '환급·추가 납부액과 항목별 계산 근거' },
] as const;

/** 최초 진입: 개인 / 맞벌이 부부 입력 방식 선택. */
export function ModeSelectPage() {
  return (
    <section className="mode-select" aria-label="입력 방식 선택">
      <div className="hero">
        <p className="hero__eyebrow">연말정산 미리 계산하기</p>
        <h2 className="hero__title">올해 연말정산, 얼마나 돌려받을까요?</h2>
        <p className="hero__desc">
          예상 급여와 공제 항목을 입력하면 결정세액과 환급·추가 납부액을 단계별 근거와 함께
          보여드립니다.
        </p>
      </div>

      <div className="mode-select__grid">
        <Link to="/individual" className="mode-card mode-card--primary">
          <span className="mode-card__icon" aria-hidden="true">
            👤
          </span>
          <strong className="mode-card__title">개인</strong>
          <span className="mode-card__desc">
            본인의 급여와 공제 항목을 입력해 환급·추가 납부액을 계산합니다.
          </span>
          <span className="mode-card__cta" aria-hidden="true">
            시작하기 →
          </span>
        </Link>
        <Link to="/couple" className="mode-card">
          <span className="mode-card__icon" aria-hidden="true">
            👫
          </span>
          <strong className="mode-card__title">맞벌이 부부</strong>
          <span className="mode-card__desc">
            부부 각자의 정보를 입력하면, 부양가족과 의료비·교육비를 누가 공제받는 것이 유리한지 모든
            경우를 계산해 추천합니다.
          </span>
          <span className="mode-card__cta" aria-hidden="true">
            시작하기 →
          </span>
        </Link>
        <Link to="/saved" className="mode-card mode-card--subtle">
          <span className="mode-card__icon" aria-hidden="true">
            📂
          </span>
          <strong className="mode-card__title">저장한 시뮬레이션 불러오기</strong>
          <span className="mode-card__desc">
            작년 데이터를 올해로 이월하거나, 저장해 둔 결과를 비교·수정합니다.
          </span>
          <span className="mode-card__cta" aria-hidden="true">
            목록 보기 →
          </span>
        </Link>
      </div>

      <ol className="how-it-works" aria-label="계산 순서">
        {HOW_IT_WORKS.map((s, i) => (
          <li key={s.title}>
            <span className="how-it-works__num" aria-hidden="true">
              {i + 1}
            </span>
            <div>
              <strong>{s.title}</strong>
              <p>{s.desc}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
