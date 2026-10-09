import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import type { UseFormReturn } from 'react-hook-form';
import { api } from '../../api/client';
import type { GlobalIncomeInput } from '../../api/types';
import { useDebouncedValue } from '../../lib/useDebouncedValue';
import { simulationInputSchema, type SimulationFormValues } from '../simulation/schema';
import { globalExtraSchema, type GlobalExtraValues } from './schema';

const DEBOUNCE_MS = 350;

/** 근로·공제 입력 + 사업·기타소득 입력이 바뀔 때마다 종합소득세를 계산한다 (백엔드). */
export function useGlobalCalculation(
  taxYear: number,
  base: UseFormReturn<SimulationFormValues>,
  extra: UseFormReturn<GlobalExtraValues>,
) {
  const b = base.watch();
  const e = extra.watch();
  const serialized = JSON.stringify({ taxYear, b, e });
  const debounced = useDebouncedValue(serialized, DEBOUNCE_MS);

  const input = useMemo((): GlobalIncomeInput | undefined => {
    const raw = JSON.parse(debounced) as { taxYear: number; b: unknown; e: unknown };
    const bp = simulationInputSchema.safeParse(raw.b);
    const ep = globalExtraSchema.safeParse(raw.e);
    if (!bp.success || !ep.success) return undefined;
    return { tax_year: raw.taxYear, base: { ...bp.data, tax_year: raw.taxYear }, ...ep.data };
  }, [debounced]);

  const query = useQuery({
    queryKey: ['global-calculate', debounced],
    queryFn: () => api.calculateGlobal(input as GlobalIncomeInput),
    enabled: input !== undefined && debounced === serialized,
    placeholderData: keepPreviousData,
  });

  return {
    input,
    result: query.data,
    error: query.error,
    isFetching: query.isFetching || debounced !== serialized,
  };
}
