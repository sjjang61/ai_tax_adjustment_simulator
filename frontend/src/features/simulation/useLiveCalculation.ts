import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { useWatch, type Control } from 'react-hook-form';
import { api } from '../../api/client';
import { useDebouncedValue } from '../../lib/useDebouncedValue';
import { simulationInputSchema, type SimulationFormValues } from './schema';

export const LIVE_CALC_DEBOUNCE_MS = 300;

/**
 * 입력이 바뀔 때마다(디바운스) 백엔드 /simulations/calculate 로 미리보기 결과를 받는다.
 * 형식 검증을 통과한 입력만 전송한다.
 */
export function useLiveCalculation(control: Control<SimulationFormValues>) {
  const values = useWatch({ control }) as SimulationFormValues;
  // useWatch는 매 렌더 새 객체를 줄 수 있어 직렬화 문자열로 안정화한다.
  const serialized = JSON.stringify(values);
  const debounced = useDebouncedValue(serialized, LIVE_CALC_DEBOUNCE_MS);
  const parsed = useMemo(() => simulationInputSchema.safeParse(JSON.parse(debounced)), [debounced]);

  const query = useQuery({
    queryKey: ['calculate', debounced],
    queryFn: () => {
      if (!parsed.success) throw new Error('invalid input');
      return api.calculate(parsed.data);
    },
    enabled: parsed.success,
    placeholderData: keepPreviousData,
  });

  return {
    /** 형식 검증을 통과한 최신(디바운스) 입력 */
    input: parsed.success ? parsed.data : undefined,
    result: query.data,
    isFetching: query.isFetching || debounced !== serialized,
    error: query.error,
    inputValid: parsed.success,
  };
}
