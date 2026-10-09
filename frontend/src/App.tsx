import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { ComparePage } from './features/compare/ComparePage';
import { CouplePage } from './features/couple/CouplePage';
import { SavedSimulationsPage } from './features/import/SavedSimulationsPage';
import { SimulationPage } from './features/simulation/SimulationPage';
import { ModeSelectPage } from './features/start/ModeSelectPage';

/** 입력·계산 화면(개인·맞벌이·저장본 편집)에 있으면 「새 시뮬레이션」 메뉴를 활성으로 표시한다. */
const SIMULATION_PATHS = /^\/($|individual|couple|simulations\/)/;
const SAVED_PATHS = /^\/(saved|compare\/)/;

export function App() {
  const { pathname } = useLocation();
  return (
    <div className="app">
      <header className="app__header">
        <div className="app__header-inner">
          <Link to="/" className="app__brand">
            <span className="app__logo" aria-hidden="true">
              ₩
            </span>
            <span className="app__title">연말정산 시뮬레이터</span>
          </Link>
          <nav className="app__nav" aria-label="주요 메뉴">
            <NavLink to="/" className={() => (SIMULATION_PATHS.test(pathname) ? 'active' : '')}>
              새 시뮬레이션
            </NavLink>
            <NavLink to="/saved" className={() => (SAVED_PATHS.test(pathname) ? 'active' : '')}>
              저장·불러오기
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="app__main">
        <Routes>
          <Route path="/" element={<ModeSelectPage />} />
          <Route path="/individual" element={<SimulationPage />} />
          <Route path="/couple" element={<CouplePage />} />
          <Route path="/simulations/:id" element={<SimulationPage />} />
          <Route path="/saved" element={<SavedSimulationsPage />} />
          <Route path="/compare/:baseId/:targetId" element={<ComparePage />} />
          <Route path="*" element={<p className="empty">페이지를 찾을 수 없습니다.</p>} />
        </Routes>
      </main>
      <footer className="app__footer">
        참고용 시뮬레이션입니다. 정확한 금액은 국세청 홈택스 연말정산 간소화 서비스 및 회사 정산
        결과를 확인하세요.
      </footer>
    </div>
  );
}
