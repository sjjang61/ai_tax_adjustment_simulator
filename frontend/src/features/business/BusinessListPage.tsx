import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { formatWon } from '../../lib/format';

/** 사업자 소득관리 목록. */
export function BusinessListPage() {
  const queryClient = useQueryClient();
  const list = useQuery({ queryKey: ['businesses'], queryFn: () => api.listBusinesses() });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteBusiness(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['businesses'] }),
  });

  return (
    <section className="panel" aria-label="사업자 소득관리">
      <header className="panel__header">
        <h2>사업자 소득관리</h2>
        <Link to="/global-income/businesses/new" className="btn btn--primary btn--small">
          + 사업자 등록
        </Link>
      </header>
      <p className="section__note">
        사업장별 수입·경비와 공동대표 지분(예: 5:5, 6:4)을 관리합니다. 종합소득세 계산 때 본인
        지분만큼 불러오거나, 공동대표 전원의 종합소득세를 한 번에 계산할 수 있습니다.
      </p>
      <ApiErrorMessage error={list.error ?? remove.error} />
      {list.isPending ? <p className="empty">불러오는 중…</p> : null}
      {list.data && list.data.length === 0 ? (
        <div className="empty-state">
          <p className="empty">등록된 사업자가 없습니다.</p>
        </div>
      ) : null}
      <ul className="sim-list">
        {list.data?.map((b) => (
          <li key={b.id} className="sim-list__item sim-list__item--global">
            <div className="sim-list__info">
              <Link to={`/global-income/businesses/${b.id}`} className="sim-list__name">
                {b.name}
              </Link>
              <span className="tag">{b.tax_year}년 귀속</span>
              <span className="tag tag--business">
                {b.partner_count > 1 ? `공동대표 ${b.partner_count}인` : '단독'}
              </span>
              <span className="sim-list__meta">소득금액 {formatWon(b.income_amount)}</span>
            </div>
            <div className="sim-list__actions">
              {b.partner_count > 1 ? (
                <Link
                  to={`/global-income/businesses/${b.id}/partnership`}
                  className="btn btn--secondary btn--small"
                >
                  공동대표 일괄 계산
                </Link>
              ) : null}
              <button
                type="button"
                className="btn btn--danger btn--small"
                onClick={() => {
                  if (window.confirm(`"${b.name}"을(를) 삭제할까요?`)) remove.mutate(b.id);
                }}
              >
                삭제
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
