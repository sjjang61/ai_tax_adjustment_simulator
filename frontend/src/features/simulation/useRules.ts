import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/client';

/** 귀속연도별 한도·공제율 메타데이터 (입력 안내문·최대값 표시용). */
export function useRules(taxYear: number) {
  return useQuery({
    queryKey: ['rules', taxYear],
    queryFn: () => api.getRules(taxYear),
    staleTime: Infinity,
    enabled: Number.isInteger(taxYear),
  });
}

export function useRuleYears() {
  return useQuery({ queryKey: ['rules'], queryFn: api.getRuleYears, staleTime: Infinity });
}
