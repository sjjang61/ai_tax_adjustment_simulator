import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import type { SimulationRead } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { describeBalance, formatWon } from '../../lib/format';

type ImportYearEndStepProps = {
  taxYear: number;
  supportedYears: readonly number[];
  onChangeYear: (year: number) => void;
  /** 선택한 연말정산 결과를 근로소득·공제 입력으로 불러온다. */
  onImport: (simulation: SimulationRead) => void;
  /** 불러오지 않고 새로 입력한다. */
  onStartFresh: () => void;
  importedName: string | null;
};

/** 1단계: 저장된 개인 연말정산 결과 불러오기 (없으면 새로 입력). */
export function ImportYearEndStep({
  taxYear,
  supportedYears,
  onChangeYear,
  onImport,
  onStartFresh,
  importedName,
}: ImportYearEndStepProps) {
  const [selectedId, setSelectedId] = useState('');
  const list = useQuery({
    queryKey: ['simulations', String(taxYear)],
    queryFn: () => api.listSimulations(taxYear),
  });
  const load = useQuery({
    queryKey: ['simulation', Number(selectedId)],
    queryFn: () => api.getSimulation(Number(selectedId)),
    enabled: false,
  });
  const items = list.data ?? [];

  return (
    <div className="step">
      <p className="step__intro">
        종합소득세는 근로소득(연말정산 결과)에 사업소득·기타소득을 더해 계산합니다. 저장해 둔 개인
        연말정산 결과가 있으면 불러와서 급여·부양가족·공제 입력을 그대로 사용하세요.
      </p>
      <div className="field" style={{ maxWidth: 240 }}>
        <label className="field__label" htmlFor="g-tax-year">
          귀속연도
        </label>
        <select
          id="g-tax-year"
          value={taxYear}
          onChange={(e) => onChangeYear(Number(e.target.value))}
        >
          {supportedYears.map((y) => (
            <option key={y} value={y}>
              {y}년 귀속
            </option>
          ))}
        </select>
      </div>

      <section className="import-individual" aria-label="연말정산 결과 불러오기">
        <div className="import-individual__head">
          <strong>📂 저장된 개인 연말정산 결과 불러오기</strong>
        </div>
        {list.isPending ? (
          <p className="preview__hint">불러오는 중…</p>
        ) : items.length === 0 ? (
          <p className="preview__hint">
            {taxYear}년 귀속으로 저장된 연말정산 결과가 없습니다. 아래 「새로 입력하기」로
            시작하거나, <Link to="/individual">연말정산 시뮬레이터</Link>에서 먼저 계산·저장할 수
            있습니다.
          </p>
        ) : (
          <div className="import-individual__row">
            <select
              aria-label="불러올 연말정산 결과"
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
            >
              <option value="">연말정산 결과 선택</option>
              {items.map((s) => {
                const b = describeBalance(s.total_balance_due);
                return (
                  <option key={s.id} value={s.id}>
                    {s.name} (결정세액 {formatWon(s.determined_tax)}, {b.label}{' '}
                    {formatWon(b.amount)})
                  </option>
                );
              })}
            </select>
            <button
              type="button"
              className="btn btn--primary btn--small"
              disabled={!selectedId || load.isFetching}
              onClick={async () => {
                const res = await load.refetch();
                if (res.data) onImport(res.data);
              }}
            >
              불러오기
            </button>
          </div>
        )}
        <ApiErrorMessage error={list.error ?? load.error} />
        {importedName ? (
          <div className="import-individual__done" role="status">
            <p>✓ 「{importedName}」의 근로소득·공제 입력을 불러왔습니다.</p>
            <ul>
              <li>근로소득 기납부세액은 연말정산 결정세액으로 계산합니다.</li>
              <li>
                다음 단계에서 내용을 확인·수정하고, 「사업·기타 소득」 단계에서 소득을 추가하세요.
              </li>
            </ul>
          </div>
        ) : null}
      </section>

      <div className="fresh-start">
        <span>불러올 결과가 없거나 근로소득이 없나요?</span>
        <button type="button" className="btn btn--ghost btn--small" onClick={onStartFresh}>
          새로 입력하기
        </button>
      </div>
    </div>
  );
}
