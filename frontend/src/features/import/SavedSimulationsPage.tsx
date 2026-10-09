import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { describeBalance, formatWon } from '../../lib/format';
import { useRuleYears } from '../simulation/useRules';
import { CarryOverForm } from './CarryOverForm';
import { downloadJson } from './download';
import { ImportPanel } from './ImportPanel';

/** 저장된 시뮬레이션 목록 + 작년 데이터 불러오기(이월)·JSON 가져오기/내보내기. */
export function SavedSimulationsPage() {
  const [yearFilter, setYearFilter] = useState<string>('');
  const [carryOverId, setCarryOverId] = useState<number | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const toggleSelected = (id: number) =>
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id].slice(-2),
    );
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const years = useRuleYears();
  const supportedYears = years.data?.supported_years ?? [];

  const list = useQuery({
    queryKey: ['simulations', yearFilter],
    queryFn: () => api.listSimulations(yearFilter ? Number(yearFilter) : undefined),
  });

  const carryOver = useMutation({
    mutationFn: (args: { id: number; targetYear: number; rate?: number }) =>
      api.carryOver(args.id, args.targetYear, args.rate),
    onSuccess: async (res) => {
      await queryClient.invalidateQueries({ queryKey: ['simulations'] });
      navigate(`/simulations/${res.simulation.id}`, {
        state: { carryOverWarnings: res.warnings },
      });
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteSimulation(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['simulations'] }),
  });

  const exportMutation = useMutation({
    mutationFn: (id: number) => api.exportSimulation(id),
    onSuccess: (doc, id) => downloadJson(doc, `simulation-${doc.tax_year}-${id}.json`),
  });

  return (
    <div className="saved">
      <section className="panel" aria-label="저장된 시뮬레이션">
        <header className="panel__header">
          <h2>저장된 시뮬레이션</h2>
          <label>
            귀속연도
            <select value={yearFilter} onChange={(e) => setYearFilter(e.target.value)}>
              <option value="">전체</option>
              {supportedYears.map((y) => (
                <option key={y} value={y}>
                  {y}년
                </option>
              ))}
            </select>
          </label>
        </header>
        <p className="section__note">
          작년 시뮬레이션의 「올해로 이월」을 누르면 부양가족 나이를 다시 계산하고 올해 규칙에 맞춘
          새 초안을 만듭니다. 원본은 바뀌지 않습니다.
        </p>

        <div className="compare-bar">
          <span>
            비교할 2건을 선택하세요 ({selected.length}/2). 먼저 고른 항목이 기준이 됩니다.
          </span>
          <button
            type="button"
            className="btn btn--primary btn--small"
            disabled={selected.length !== 2}
            onClick={() => navigate(`/compare/${selected[0]}/${selected[1]}`)}
          >
            선택한 2건 비교
          </button>
        </div>

        <ApiErrorMessage
          error={list.error ?? carryOver.error ?? remove.error ?? exportMutation.error}
        />
        {list.isPending ? <p className="empty">불러오는 중…</p> : null}
        {list.data && list.data.length === 0 ? (
          <div className="empty-state">
            <p className="empty">저장된 시뮬레이션이 없습니다.</p>
            <Link to="/" className="btn btn--primary btn--small">
              새 시뮬레이션 시작
            </Link>
          </div>
        ) : null}

        <ul className="sim-list">
          {list.data?.map((sim) => {
            const balance = describeBalance(sim.total_balance_due);
            return (
              <li key={sim.id} className="sim-list__item">
                <input
                  type="checkbox"
                  className="sim-list__check"
                  aria-label={`${sim.name} 비교 선택`}
                  checked={selected.includes(sim.id)}
                  onChange={() => toggleSelected(sim.id)}
                />
                <div className="sim-list__info">
                  <Link to={`/simulations/${sim.id}`} className="sim-list__name">
                    {sim.name}
                  </Link>
                  <span className="tag">{sim.tax_year}년 귀속</span>
                  <span className={`sim-list__balance sim-list__balance--${balance.kind}`}>
                    {balance.label} {formatWon(balance.amount)}
                  </span>
                  <span className="sim-list__meta">
                    결정세액 {formatWon(sim.determined_tax)} · 수정{' '}
                    {new Date(sim.updated_at).toLocaleDateString('ko-KR')}
                  </span>
                </div>
                <div className="sim-list__actions">
                  <button
                    type="button"
                    className="btn btn--secondary btn--small"
                    onClick={() => setCarryOverId(carryOverId === sim.id ? null : sim.id)}
                  >
                    올해로 이월
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--small"
                    onClick={() => exportMutation.mutate(sim.id)}
                  >
                    내보내기
                  </button>
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
                {carryOverId === sim.id ? (
                  <CarryOverForm
                    sourceYear={sim.tax_year}
                    supportedYears={supportedYears}
                    pending={carryOver.isPending}
                    onCancel={() => setCarryOverId(null)}
                    onSubmit={(targetYear, rate) =>
                      carryOver.mutate({ id: sim.id, targetYear, rate })
                    }
                  />
                ) : null}
              </li>
            );
          })}
        </ul>
      </section>

      <ImportPanel
        supportedYears={supportedYears}
        defaultYear={years.data?.default_tax_year ?? supportedYears[0] ?? 2025}
      />
    </div>
  );
}
