import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../api/client';
import type { SimulationRead, Spouse } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { describeBalance, formatWon } from '../../lib/format';
import { SPOUSE_LABELS } from './schema';

type ImportIndividualPanelProps = {
  who: Spouse;
  taxYear: number;
  /** 선택한 개인 시뮬레이션을 받아 맞벌이 입력에 반영하고, 안내 문구를 돌려준다. */
  onImport: (simulation: SimulationRead) => string[];
};

/** 맞벌이 입력: 저장된 개인 시뮬레이션에서 본인/배우자 정보 불러오기. */
export function ImportIndividualPanel({ who, taxYear, onImport }: ImportIndividualPanelProps) {
  const [selectedId, setSelectedId] = useState<string>('');
  const [notes, setNotes] = useState<string[] | null>(null);
  const [showAllYears, setShowAllYears] = useState(false);
  const list = useQuery({
    queryKey: ['simulations', showAllYears ? '' : String(taxYear)],
    queryFn: () => api.listSimulations(showAllYears ? undefined : taxYear),
  });
  const load = useMutation({
    mutationFn: (id: number) => api.getSimulation(id),
    onSuccess: (sim) => setNotes(onImport(sim)),
  });
  const label = SPOUSE_LABELS[who];
  // 조사: 받침 있는 '본인'은 '으로', '배우자'는 '로'
  const asLabel = who === 'primary' ? `${label}으로` : `${label}로`;
  const items = list.data ?? [];

  return (
    <section className="import-individual" aria-label={`${label} 정보 불러오기`}>
      <div className="import-individual__head">
        <strong>📂 저장된 개인 시뮬레이션에서 불러오기</strong>
        <label className="import-individual__all">
          <input
            type="checkbox"
            checked={showAllYears}
            onChange={(e) => setShowAllYears(e.target.checked)}
          />
          다른 귀속연도도 보기
        </label>
      </div>
      {list.isPending ? (
        <p className="preview__hint">불러오는 중…</p>
      ) : items.length === 0 ? (
        <p className="preview__hint">
          {showAllYears ? '저장된' : `${taxYear}년 귀속으로 저장된`} 개인 시뮬레이션이 없습니다.
        </p>
      ) : (
        <div className="import-individual__row">
          <select
            aria-label={`${asLabel} 불러올 시뮬레이션`}
            value={selectedId}
            onChange={(e) => {
              setSelectedId(e.target.value);
              setNotes(null);
            }}
          >
            <option value="">시뮬레이션 선택</option>
            {items.map((s) => {
              const b = describeBalance(s.total_balance_due);
              return (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.tax_year}년, {b.label} {formatWon(b.amount)})
                </option>
              );
            })}
          </select>
          <button
            type="button"
            className="btn btn--secondary btn--small"
            disabled={!selectedId || load.isPending}
            onClick={() => load.mutate(Number(selectedId))}
          >
            {label} 정보로 불러오기
          </button>
        </div>
      )}
      <ApiErrorMessage error={list.error ?? load.error} />
      {notes ? (
        <div className="import-individual__done" role="status">
          <p>
            ✓ {load.data?.name}을(를) {label} 정보로 불러왔습니다.
          </p>
          {notes.length > 0 ? (
            <ul>
              {notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
