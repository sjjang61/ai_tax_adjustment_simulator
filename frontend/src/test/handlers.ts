import { http, HttpResponse } from 'msw';
import type {
  BusinessAllocation,
  BusinessRead,
  BusinessRecord,
  BusinessSummary,
  PartnershipResult,
  GlobalIncomeInput,
  GlobalIncomeResult,
  GlobalIncomeSimulationRead,
  GlobalIncomeSimulationSummary,
  ComparisonResult,
  SimulationComparison,
  CoupleOptimizationResult,
  CoupleRecommendationResponse,
  RecommendationResponse,
  RulesYears,
  SimulationExport,
  SimulationInput,
  SimulationRead,
  SimulationSummary,
  SimulationWithWarnings,
  TaxResult,
  TaxRules,
} from '../api/types';
import businessAllocationFixture from './fixtures/business-allocation.json';
import businessRecordFixture from './fixtures/business-record.json';
import comparisonFixture from './fixtures/comparison.json';
import partnershipFixture from './fixtures/partnership.json';
import coupleResultFixture from './fixtures/couple-result.json';
import globalResultFixture from './fixtures/global-result.json';
import inputFixture from './fixtures/input.json';
import resultFixture from './fixtures/result.json';
import rulesFixture from './fixtures/rules-2025.json';
import rules2026Fixture from './fixtures/rules-2026.json';

export const BASE = 'http://api.test/api/v1';

export const fixtureInput = inputFixture as SimulationInput;
export const fixtureResult = resultFixture as TaxResult;
export const fixtureRules = rulesFixture as TaxRules;
export const fixtureCoupleResult = coupleResultFixture as CoupleOptimizationResult;

/** 테스트 간 공유되는 가짜 DB. resetDb()로 초기화한다. */
export const db = {
  simulations: new Map<number, SimulationRead>(),
  globals: new Map<number, GlobalIncomeSimulationRead>(),
  businesses: new Map<number, BusinessRead>(),
  nextId: 1,
};
export const fixtureGlobalResult = globalResultFixture as GlobalIncomeResult;
export const fixtureAllocation = businessAllocationFixture as BusinessAllocation;
export const fixtureBusinessRecord = businessRecordFixture as BusinessRecord;
export const fixturePartnership = partnershipFixture as PartnershipResult;

export function storeBusiness(id: number, record: BusinessRecord): BusinessRead {
  const b: BusinessRead = {
    id,
    name: record.name,
    tax_year: record.tax_year,
    partner_count: record.partners.length,
    income_amount: fixtureAllocation.income_amount,
    updated_at: '2026-05-01T00:00:00Z',
    record: {
      ...record,
      expense_rate: String(record.expense_rate ?? '0'),
    } as BusinessRead['record'],
    allocation: fixtureAllocation,
  };
  db.businesses.set(id, b);
  return b;
}

export function makeSimulation(
  partial: Partial<SimulationRead> & Pick<SimulationRead, 'name'>,
): SimulationRead {
  const id = partial.id ?? db.nextId++;
  const input = partial.input ?? fixtureInput;
  return {
    id,
    tax_year: input.tax_year,
    schema_version: 1,
    determined_tax: fixtureResult.determined_tax,
    total_balance_due: fixtureResult.total_balance_due,
    source_simulation_id: null,
    created_at: '2026-01-10T00:00:00Z',
    updated_at: '2026-01-10T00:00:00Z',
    input,
    result: { ...fixtureResult, tax_year: input.tax_year },
    ...partial,
  };
}

export function resetDb(): void {
  db.simulations.clear();
  db.globals.clear();
  db.businesses.clear();
  db.nextId = 1;
}

function summary(sim: SimulationRead): SimulationSummary {
  return {
    id: sim.id,
    name: sim.name,
    tax_year: sim.tax_year,
    schema_version: sim.schema_version,
    determined_tax: sim.determined_tax,
    total_balance_due: sim.total_balance_due,
    source_simulation_id: sim.source_simulation_id,
    created_at: sim.created_at,
    updated_at: sim.updated_at,
  };
}

export function makeRecommendations(input: SimulationInput): RecommendationResponse {
  return {
    model: 'gpt-5.6-luna',
    summary: '연금계좌 세액공제 한도가 남아 있습니다.',
    base_total_balance_due: fixtureResult.total_balance_due,
    recommendations: [
      {
        title: 'IRP 추가 납입',
        category: 'tax_credit',
        reason: '연금저축과 IRP 합산 한도 900만원 중 300만원이 남았습니다.',
        action: '12월 31일 전에 IRP 계좌에 납입하세요.',
        adjustment_field: 'credits.irp',
        adjustment_label: '퇴직연금(IRP) 납입액',
        additional_amount: 3_000_000,
        estimated_saving: 396_000,
        adjusted_input: { ...input, credits: { ...input.credits, irp: 3_000_000 } },
      },
      {
        title: '부양가족 등록 확인',
        category: 'eligibility_check',
        reason: '부양가족이 등록되어 있지 않습니다.',
        action: '소득 요건을 충족하는 가족이 있는지 확인하세요.',
        adjustment_field: null,
        adjustment_label: null,
        additional_amount: null,
        estimated_saving: null,
        adjusted_input: null,
      },
    ],
    discarded_count: 0,
    disclaimer: 'AI 추천은 참고용입니다.',
  };
}

export const fixtureComparison = comparisonFixture as ComparisonResult;

/** 변경안이 IRP 300만원 추가면 실제 엔진 비교 결과, 입력이 같으면 "차이 없음"을 돌려준다. */
export function makeComparison(base: SimulationRead, input: SimulationInput): SimulationComparison {
  const same = JSON.stringify(base.input) === JSON.stringify(input);
  const comparison: ComparisonResult = same
    ? {
        ...fixtureComparison,
        after: fixtureComparison.before,
        saving: 0,
        metrics: fixtureComparison.metrics.map((m) => ({ ...m, after: m.before, delta: 0 })),
        income_deduction_diffs: [],
        tax_credit_diffs: [],
        input_diffs: [],
      }
    : fixtureComparison;
  return { base: summary(base), snapshot_differs: false, comparison };
}

function storeGlobal(
  id: number,
  name: string,
  input: GlobalIncomeInput,
  sourceId: number | null,
): GlobalIncomeSimulationRead {
  const sim: GlobalIncomeSimulationRead = {
    id,
    name,
    tax_year: input.tax_year,
    total_balance_due: fixtureGlobalResult.total_balance_due,
    source_simulation_id: sourceId,
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
    input: {
      ...input,
      business_incomes: input.business_incomes.map((b) => ({
        ...b,
        expense_rate: String(b.expense_rate),
      })),
    } as GlobalIncomeSimulationRead['input'],
    result: fixtureGlobalResult,
  };
  db.globals.set(id, sim);
  return sim;
}

export const handlers = [
  http.post(`${BASE}/businesses/allocate`, () =>
    HttpResponse.json<BusinessAllocation>(fixtureAllocation),
  ),
  http.post(`${BASE}/businesses/partnership`, () =>
    HttpResponse.json<PartnershipResult>(fixturePartnership),
  ),
  http.get(`${BASE}/businesses`, () =>
    HttpResponse.json<BusinessSummary[]>(
      [...db.businesses.values()].map((b) => ({
        id: b.id,
        name: b.name,
        tax_year: b.tax_year,
        partner_count: b.partner_count,
        income_amount: b.income_amount,
        updated_at: b.updated_at,
      })),
    ),
  ),
  http.post(`${BASE}/businesses`, async ({ request }) => {
    const body = (await request.json()) as { record: BusinessRecord };
    return HttpResponse.json(storeBusiness(db.nextId++, body.record), { status: 201 });
  }),
  http.get(`${BASE}/businesses/:id`, ({ params }) => {
    const b = db.businesses.get(Number(params.id));
    return b
      ? HttpResponse.json(b)
      : HttpResponse.json({ code: 'not_found', message: 'x', details: null }, { status: 404 });
  }),
  http.put(`${BASE}/businesses/:id`, async ({ params, request }) => {
    const body = (await request.json()) as { record: BusinessRecord };
    return HttpResponse.json(storeBusiness(Number(params.id), body.record));
  }),
  http.delete(`${BASE}/businesses/:id`, ({ params }) => {
    db.businesses.delete(Number(params.id));
    return new HttpResponse(null, { status: 204 });
  }),
  http.post(`${BASE}/global-income/calculate`, () =>
    HttpResponse.json<GlobalIncomeResult>(fixtureGlobalResult),
  ),
  http.get(`${BASE}/global-income/simulations`, () =>
    HttpResponse.json<GlobalIncomeSimulationSummary[]>(
      [...db.globals.values()].map(({ input: _i, result: _r, ...rest }) => {
        void _i;
        void _r;
        return rest;
      }),
    ),
  ),
  http.post(`${BASE}/global-income/simulations`, async ({ request }) => {
    const body = (await request.json()) as {
      name: string;
      input: GlobalIncomeInput;
      source_simulation_id: number | null;
    };
    const sim = storeGlobal(db.nextId++, body.name, body.input, body.source_simulation_id);
    return HttpResponse.json(sim, { status: 201 });
  }),
  http.get(`${BASE}/global-income/simulations/:id`, ({ params }) => {
    const sim = db.globals.get(Number(params.id));
    return sim
      ? HttpResponse.json(sim)
      : HttpResponse.json({ code: 'not_found', message: 'x', details: null }, { status: 404 });
  }),
  http.put(`${BASE}/global-income/simulations/:id`, async ({ params, request }) => {
    const body = (await request.json()) as { name: string; input: GlobalIncomeInput };
    const prev = db.globals.get(Number(params.id));
    return HttpResponse.json(
      storeGlobal(Number(params.id), body.name, body.input, prev?.source_simulation_id ?? null),
    );
  }),
  http.delete(`${BASE}/global-income/simulations/:id`, ({ params }) => {
    db.globals.delete(Number(params.id));
    return new HttpResponse(null, { status: 204 });
  }),
  http.post(`${BASE}/simulations/:id/compare`, async ({ params, request }) => {
    const base = db.simulations.get(Number(params.id));
    if (!base) {
      return HttpResponse.json({ code: 'not_found', message: 'x', details: null }, { status: 404 });
    }
    const input = (await request.json()) as SimulationInput;
    return HttpResponse.json<SimulationComparison>(makeComparison(base, input));
  }),
  http.post(`${BASE}/couples/optimize`, () =>
    HttpResponse.json<CoupleOptimizationResult>(fixtureCoupleResult),
  ),
  http.post(`${BASE}/couples/recommendations`, () =>
    HttpResponse.json<CoupleRecommendationResponse>({
      model: 'gpt-5.6-luna',
      summary: '어머니는 배우자가, 첫째는 본인이 공제받는 것이 유리합니다.',
      dependent_reasons: [
        {
          index: 0,
          name: '어머니',
          recommended_to: 'spouse',
          reason: '의료비 공제 문턱이 낮습니다.',
        },
        { index: 1, name: '첫째', recommended_to: 'primary', reason: '한계세율이 높습니다.' },
      ],
      tips: ['신용카드는 총급여 25% 문턱을 넘는 쪽에 사용을 모으세요.'],
      disclaimer: 'AI 설명은 참고용입니다.',
    }),
  ),
  http.post(`${BASE}/recommendations`, async ({ request }) => {
    const input = (await request.json()) as SimulationInput;
    return HttpResponse.json<RecommendationResponse>(makeRecommendations(input));
  }),
  http.post(`${BASE}/simulations/calculate`, async ({ request }) => {
    const input = (await request.json()) as SimulationInput;
    return HttpResponse.json<TaxResult>({ ...fixtureResult, tax_year: input.tax_year });
  }),
  http.get(`${BASE}/simulations`, () =>
    HttpResponse.json<SimulationSummary[]>([...db.simulations.values()].map(summary)),
  ),
  http.post(`${BASE}/simulations`, async ({ request }) => {
    const body = (await request.json()) as { name: string; input: SimulationInput };
    const sim = makeSimulation({ name: body.name, input: body.input });
    db.simulations.set(sim.id, sim);
    return HttpResponse.json(sim, { status: 201 });
  }),
  http.post(`${BASE}/simulations/import`, async ({ request }) => {
    const doc = (await request.json()) as SimulationExport;
    const target = new URL(request.url).searchParams.get('target_year');
    const input = { ...(doc.input as SimulationInput) };
    if (target) input.tax_year = Number(target);
    const sim = makeSimulation({ name: doc.name, input });
    db.simulations.set(sim.id, sim);
    return HttpResponse.json<SimulationWithWarnings>(
      { simulation: sim, warnings: [] },
      { status: 201 },
    );
  }),
  http.get(`${BASE}/simulations/:id`, ({ params }) => {
    const sim = db.simulations.get(Number(params.id));
    return sim
      ? HttpResponse.json(sim)
      : HttpResponse.json(
          { code: 'not_found', message: '시뮬레이션을 찾을 수 없습니다', details: null },
          { status: 404 },
        );
  }),
  http.put(`${BASE}/simulations/:id`, async ({ params, request }) => {
    const body = (await request.json()) as { name: string; input: SimulationInput };
    const sim = makeSimulation({ id: Number(params.id), name: body.name, input: body.input });
    db.simulations.set(sim.id, sim);
    return HttpResponse.json(sim);
  }),
  http.delete(`${BASE}/simulations/:id`, ({ params }) => {
    db.simulations.delete(Number(params.id));
    return new HttpResponse(null, { status: 204 });
  }),
  http.post(`${BASE}/simulations/:id/carry-over`, ({ params, request }) => {
    const source = db.simulations.get(Number(params.id));
    const target = Number(new URL(request.url).searchParams.get('target_year'));
    if (!source) {
      return HttpResponse.json({ code: 'not_found', message: 'x', details: null }, { status: 404 });
    }
    const sim = makeSimulation({
      name: `${source.name} → ${target}년 초안`,
      input: { ...source.input, tax_year: target },
      source_simulation_id: source.id,
    });
    db.simulations.set(sim.id, sim);
    return HttpResponse.json<SimulationWithWarnings>(
      {
        simulation: sim,
        warnings: [
          {
            code: 'carry_over_elderly',
            message: '아버지: 70세가 되어 경로우대 추가공제 대상이 됩니다.',
            level: 'info',
            field: 'dependents[0]',
          },
        ],
      },
      { status: 201 },
    );
  }),
  http.get(`${BASE}/simulations/:id/export`, ({ params }) => {
    const sim = db.simulations.get(Number(params.id));
    if (!sim) {
      return HttpResponse.json({ code: 'not_found', message: 'x', details: null }, { status: 404 });
    }
    return HttpResponse.json<SimulationExport>({
      schema_version: 1,
      tax_year: sim.tax_year,
      name: sim.name,
      exported_at: '2026-01-10T00:00:00Z',
      input: sim.input as unknown as SimulationExport['input'],
    });
  }),
  http.get(`${BASE}/rules`, () =>
    HttpResponse.json<RulesYears>({ supported_years: [2025, 2026], default_tax_year: 2025 }),
  ),
  http.get(`${BASE}/rules/:year`, ({ params }) =>
    HttpResponse.json<TaxRules>(
      Number(params.year) === 2026 ? (rules2026Fixture as TaxRules) : fixtureRules,
    ),
  ),
];
