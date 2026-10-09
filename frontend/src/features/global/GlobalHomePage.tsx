import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { describeBalance, formatWon } from '../../lib/format';

/** 종합소득세 시뮬레이터 첫 화면: 새 계산 + 저장 목록. */
export function GlobalHomePage() {
  const queryClient = useQueryClient();
  const list = useQuery({
    queryKey: ['global-simulations'],
    queryFn: () => api.listGlobalSimulations(),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteGlobalSimulation(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['global-simulations'] }),
  });

  return (
    <div className="saved">
      <div className="hero">
        <p className="hero__eyebrow">종합소득세 미리 계산하기</p>
        <h2 className="hero__title">근로소득에 사업·기타소득까지 합쳐 계산합니다</h2>
        <p className="hero__desc">
          저장해 둔 연말정산 결과를 그대로 불러온 뒤 프리랜서·부업 등 사업소득과 강연료·원고료 등
          기타소득을 더하면, 5월 종합소득세 신고 때 더 낼 세금이나 돌려받을 세금을 계산합니다.
        </p>
        <Link to="/global-income/new" className="btn btn--primary btn--lg hero__cta">
          새로 계산하기
        </Link>
      </div>

      <section className="panel" aria-label="저장된 종합소득세 시뮬레이션">
        <h2>저장된 종합소득세 시뮬레이션</h2>
        <ApiErrorMessage error={list.error ?? remove.error} />
        {list.isPending ? <p className="empty">불러오는 중…</p> : null}
        {list.data && list.data.length === 0 ? (
          <div className="empty-state">
            <p className="empty">저장된 종합소득세 시뮬레이션이 없습니다.</p>
          </div>
        ) : null}
        <ul className="sim-list">
          {list.data?.map((sim) => {
            const b = describeBalance(sim.total_balance_due);
            return (
              <li key={sim.id} className="sim-list__item sim-list__item--global">
                <div className="sim-list__info">
                  <Link to={`/global-income/${sim.id}`} className="sim-list__name">
                    {sim.name}
                  </Link>
                  <span className="tag">{sim.tax_year}년 귀속</span>
                  <span className={`sim-list__balance sim-list__balance--${b.kind}`}>
                    {b.kind === 'payment' ? '납부' : b.label} {formatWon(b.amount)}
                  </span>
                  <span className="sim-list__meta">
                    {sim.source_simulation_id ? '연말정산 결과 연동 · ' : ''}수정{' '}
                    {new Date(sim.updated_at).toLocaleDateString('ko-KR')}
                  </span>
                </div>
                <div className="sim-list__actions">
                  <button
                    type="button"
                    className="btn btn--danger btn--small"
                    onClick={() => {
                      if (window.confirm(`"${sim.name}"을(를) 삭제할까요?`)) remove.mutate(sim.id);
                    }}
                  >
                    삭제
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
