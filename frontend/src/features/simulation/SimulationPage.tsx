import { useQuery } from '@tanstack/react-query';
import { useLocation, useParams } from 'react-router-dom';
import { api } from '../../api/client';
import type { CalcWarning } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { WarningList } from '../../components/WarningList';
import { emptyInput } from './defaults';
import { SimulationWizard } from './SimulationWizard';
import { useRuleYears } from './useRules';

export type SimulationLocationState = { carryOverWarnings?: CalcWarning[]; step?: number } | null;

/** 새 시뮬레이션(/) 또는 저장된 시뮬레이션(/simulations/:id) 편집 화면. */
export function SimulationPage() {
  const { id } = useParams();
  const simulationId = id ? Number(id) : undefined;
  const location = useLocation();
  const state = location.state as SimulationLocationState;
  const years = useRuleYears();

  const loaded = useQuery({
    queryKey: ['simulation', simulationId],
    queryFn: () => api.getSimulation(simulationId as number),
    enabled: simulationId !== undefined,
  });

  if (simulationId !== undefined) {
    if (loaded.isPending) return <p className="empty">불러오는 중…</p>;
    if (loaded.error) return <ApiErrorMessage error={loaded.error} />;
    const sim = loaded.data;
    return (
      <>
        {state?.carryOverWarnings ? (
          <WarningList warnings={state.carryOverWarnings} title="작년 데이터 이월 결과 확인" />
        ) : null}
        <SimulationWizard
          key={sim.id}
          simulationId={sim.id}
          initialName={sim.name}
          initialInput={sim.input}
          initialStep={state?.step}
        />
      </>
    );
  }

  if (years.isPending) return <p className="empty">불러오는 중…</p>;
  const defaultYear = years.data?.default_tax_year ?? 2025;
  return <SimulationWizard key="new" initialInput={emptyInput(defaultYear)} />;
}
