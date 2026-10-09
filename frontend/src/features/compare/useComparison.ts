import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '../../api/client';
import type { SimulationInput } from '../../api/types';

/** 저장본(simulationId)과 변경안(input) 비교. input은 이미 디바운스·형식 검증된 값을 넘긴다. */
export function useComparison(
  simulationId: number | undefined,
  input: SimulationInput | undefined,
) {
  return useQuery({
    queryKey: ['compare', simulationId, input ? JSON.stringify(input) : null],
    queryFn: () => api.compareSimulation(simulationId as number, input as SimulationInput),
    enabled: simulationId !== undefined && input !== undefined,
    placeholderData: keepPreviousData,
  });
}
