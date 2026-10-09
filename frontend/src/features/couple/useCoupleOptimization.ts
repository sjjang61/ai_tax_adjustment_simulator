import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import type { UseFormReturn } from 'react-hook-form';
import { api } from '../../api/client';
import type { CoupleInput } from '../../api/types';
import { useDebouncedValue } from '../../lib/useDebouncedValue';
import { simulationInputSchema, type SimulationFormValues } from '../simulation/schema';
import { sharedFormSchema, type SharedFormValues } from './schema';

const DEBOUNCE_MS = 400;

/** 부부 입력이 바뀔 때마다(디바운스) /couples/optimize 로 최적 배분을 계산한다. */
export function useCoupleOptimization(
  taxYear: number,
  primary: UseFormReturn<SimulationFormValues>,
  spouse: UseFormReturn<SimulationFormValues>,
  shared: UseFormReturn<SharedFormValues>,
  enabled: boolean,
) {
  // 부부·공유 부양가족 세 폼의 모든 변경을 구독한다.
  const p = primary.watch();
  const s = spouse.watch();
  const d = shared.watch();
  const serialized = JSON.stringify({ taxYear, p, s, d });
  const debounced = useDebouncedValue(serialized, DEBOUNCE_MS);

  const input = useMemo((): CoupleInput | undefined => {
    const raw = JSON.parse(debounced) as { taxYear: number; p: unknown; s: unknown; d: unknown };
    const pp = simulationInputSchema.safeParse(raw.p);
    const sp = simulationInputSchema.safeParse(raw.s);
    const dp = sharedFormSchema.safeParse(raw.d);
    if (!pp.success || !sp.success || !dp.success) return undefined;
    // 귀속연도는 부부 공통 선택값으로 맞춘다 (폼 초기화 시점과 기본 연도 로딩 순서 차이 방지)
    return {
      tax_year: raw.taxYear,
      primary: { ...pp.data, tax_year: raw.taxYear },
      spouse: { ...sp.data, tax_year: raw.taxYear },
      shared_dependents: dp.data.shared_dependents,
    };
  }, [debounced]);

  const query = useQuery({
    queryKey: ['couple-optimize', debounced],
    queryFn: () => api.optimizeCouple(input as CoupleInput),
    // 디바운스된 값이 최신 입력을 따라잡은 뒤에만 요청한다 (오래된 입력으로 계산하지 않도록)
    enabled: enabled && input !== undefined && debounced === serialized,
    placeholderData: keepPreviousData,
  });

  return {
    input,
    result: query.data,
    error: query.error,
    isFetching: query.isFetching || debounced !== serialized,
  };
}
