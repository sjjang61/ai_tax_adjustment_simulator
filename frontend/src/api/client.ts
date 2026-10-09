import type {
  CoupleInput,
  CoupleOptimizationResult,
  CoupleRecommendationResponse,
  ErrorResponse,
  RecommendationResponse,
  RulesYears,
  SimulationComparison,
  SimulationExport,
  SimulationInput,
  SimulationRead,
  SimulationSummary,
  SimulationWithWarnings,
  TaxResult,
  TaxRules,
} from './types';

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

/** 백엔드 통일 에러 응답({code, message, details})을 담는 예외. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ErrorResponse['details'];

  constructor(status: number, body: ErrorResponse) {
    super(body.message);
    this.name = 'ApiError';
    this.status = status;
    this.code = body.code;
    this.details = body.details;
  }
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as { code?: unknown }).code === 'string' &&
    typeof (value as { message?: unknown }).message === 'string'
  );
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init.headers },
  });
  if (res.status === 204) {
    return undefined as T;
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(
      res.status,
      isErrorResponse(body)
        ? body
        : { code: 'http_error', message: `요청 실패 (${res.status})`, details: null },
    );
  }
  return body as T;
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

function query(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : '';
}

export const api = {
  calculate: (input: SimulationInput) =>
    request<TaxResult>('/simulations/calculate', { method: 'POST', ...json(input) }),
  listSimulations: (taxYear?: number) =>
    request<SimulationSummary[]>(`/simulations${query({ tax_year: taxYear })}`),
  getSimulation: (id: number) => request<SimulationRead>(`/simulations/${id}`),
  createSimulation: (name: string, input: SimulationInput) =>
    request<SimulationRead>('/simulations', { method: 'POST', ...json({ name, input }) }),
  updateSimulation: (id: number, name: string, input: SimulationInput) =>
    request<SimulationRead>(`/simulations/${id}`, { method: 'PUT', ...json({ name, input }) }),
  deleteSimulation: (id: number) => request<undefined>(`/simulations/${id}`, { method: 'DELETE' }),
  compareSimulation: (id: number, input: SimulationInput) =>
    request<SimulationComparison>(`/simulations/${id}/compare`, {
      method: 'POST',
      ...json(input),
    }),
  carryOver: (id: number, targetYear: number, salaryIncreaseRate?: number) =>
    request<SimulationWithWarnings>(
      `/simulations/${id}/carry-over${query({
        target_year: targetYear,
        salary_increase_rate: salaryIncreaseRate,
      })}`,
      { method: 'POST' },
    ),
  exportSimulation: (id: number) => request<SimulationExport>(`/simulations/${id}/export`),
  importSimulation: (doc: SimulationExport, targetYear?: number) =>
    request<SimulationWithWarnings>(`/simulations/import${query({ target_year: targetYear })}`, {
      method: 'POST',
      ...json(doc),
    }),
  recommend: (input: SimulationInput) =>
    request<RecommendationResponse>('/recommendations', { method: 'POST', ...json(input) }),
  optimizeCouple: (input: CoupleInput) =>
    request<CoupleOptimizationResult>('/couples/optimize', { method: 'POST', ...json(input) }),
  recommendCouple: (input: CoupleInput) =>
    request<CoupleRecommendationResponse>('/couples/recommendations', {
      method: 'POST',
      ...json(input),
    }),
  getRuleYears: () => request<RulesYears>('/rules'),
  getRules: (taxYear: number) => request<TaxRules>(`/rules/${taxYear}`),
};
