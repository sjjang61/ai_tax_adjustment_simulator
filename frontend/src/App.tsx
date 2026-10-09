import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { BusinessFormPage } from './features/business/BusinessFormPage';
import { BusinessListPage } from './features/business/BusinessListPage';
import { PartnershipPage } from './features/business/PartnershipPage';
import { ComparePage } from './features/compare/ComparePage';
import { CouplePage } from './features/couple/CouplePage';
import { GlobalHomePage } from './features/global/GlobalHomePage';
import { GlobalIncomePage } from './features/global/GlobalIncomePage';
import { SavedSimulationsPage } from './features/import/SavedSimulationsPage';
import { SimulationPage } from './features/simulation/SimulationPage';
import { ModeSelectPage } from './features/start/ModeSelectPage';

const GLOBAL_PATHS = /^\/global-income(\/|$)/;

type SubLink = { to: string; label: string; match: RegExp };

const YEAR_END_LINKS: SubLink[] = [
  { to: '/', label: '새 계산', match: /^\/($|individual|couple|simulations\/)/ },
  { to: '/saved', label: '저장·불러오기', match: /^\/(saved|compare\/)/ },
];
const GLOBAL_LINKS: SubLink[] = [
  { to: '/global-income/new', label: '새 계산', match: /^\/global-income\/(new|\d+)/ },
  { to: '/global-income', label: '저장 목록', match: /^\/global-income\/?$/ },
  { to: '/global-income/businesses', label: '사업자 관리', match: /^\/global-income\/businesses/ },
];

export function App() {
  const { pathname } = useLocation();
  const isGlobal = GLOBAL_PATHS.test(pathname);
  const subLinks = isGlobal ? GLOBAL_LINKS : YEAR_END_LINKS;
  return (
    <div className="app">
      <header className="app__header">
        <div className="app__header-inner">
          <Link to="/" className="app__brand">
            <span className="app__logo" aria-hidden="true">
              ₩
            </span>
            <span className="app__title">세금 시뮬레이터</span>
          </Link>
          <nav className="app__nav" aria-label="주요 메뉴">
            <NavLink to="/" className={() => (!isGlobal ? 'active' : '')}>
              연말정산 시뮬레이터
            </NavLink>
            <NavLink to="/global-income" className={() => (isGlobal ? 'active' : '')}>
              종합소득세 시뮬레이터
            </NavLink>
          </nav>
        </div>
        <nav className="app__subnav" aria-label={isGlobal ? '종합소득세 메뉴' : '연말정산 메뉴'}>
          <div className="app__subnav-inner">
            {subLinks.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end
                className={() => (l.match.test(pathname) ? 'active' : '')}
              >
                {l.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>
      <main className="app__main">
        <Routes>
          <Route path="/" element={<ModeSelectPage />} />
          <Route path="/individual" element={<SimulationPage />} />
          <Route path="/couple" element={<CouplePage />} />
          <Route path="/simulations/:id" element={<SimulationPage />} />
          <Route path="/saved" element={<SavedSimulationsPage />} />
          <Route path="/compare/:baseId/:targetId" element={<ComparePage />} />
          <Route path="/global-income" element={<GlobalHomePage />} />
          <Route path="/global-income/new" element={<GlobalIncomePage />} />
          <Route path="/global-income/businesses" element={<BusinessListPage />} />
          <Route path="/global-income/businesses/new" element={<BusinessFormPage />} />
          <Route path="/global-income/businesses/:id" element={<BusinessFormPage />} />
          <Route path="/global-income/businesses/:id/partnership" element={<PartnershipPage />} />
          <Route path="/global-income/:id" element={<GlobalIncomePage />} />
          <Route path="*" element={<p className="empty">페이지를 찾을 수 없습니다.</p>} />
        </Routes>
      </main>
      <footer className="app__footer">
        참고용 시뮬레이션입니다. 정확한 금액은 국세청 홈택스(연말정산 간소화·종합소득세 신고) 및
        회사 정산 결과를 확인하세요.
      </footer>
    </div>
  );
}
