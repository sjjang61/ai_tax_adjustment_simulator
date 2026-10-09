import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { api } from '../../api/client';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { ComparisonView } from './ComparisonView';
import { useComparison } from './useComparison';

/** 저장된 두 시뮬레이션 비교: /compare/:baseId/:targetId */
export function ComparePage() {
  const params = useParams();
  const baseId = Number(params.baseId);
  const targetId = Number(params.targetId);
  const base = useQuery({
    queryKey: ['simulation', baseId],
    queryFn: () => api.getSimulation(baseId),
  });
  const target = useQuery({
    queryKey: ['simulation', targetId],
    queryFn: () => api.getSimulation(targetId),
  });
  const comparison = useComparison(base.data ? baseId : undefined, target.data?.input);

  const error = base.error ?? target.error ?? comparison.error;
  return (
    <section className="panel" aria-label="저장된 시뮬레이션 비교">
      <h2>
        비교: {base.data?.name ?? '…'} → {target.data?.name ?? '…'}
      </h2>
      <p className="section__note">
        <Link to={`/simulations/${baseId}`}>기준 열기</Link> ·{' '}
        <Link to={`/simulations/${targetId}`}>비교 대상 열기</Link> ·{' '}
        <Link to="/saved">목록으로</Link>
      </p>
      <ApiErrorMessage error={error} />
      {comparison.data && base.data && target.data ? (
        <ComparisonView
          data={comparison.data}
          beforeLabel={`기준(${base.data.name})`}
          afterLabel={`비교 대상(${target.data.name})`}
        />
      ) : !error ? (
        <p className="empty">비교하는 중…</p>
      ) : null}
    </section>
  );
}
