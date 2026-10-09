import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { FormProvider, useForm, type FieldPath } from 'react-hook-form';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { api } from '../../api/client';
import type { SimulationInput, SimulationRead, StoredGlobalIncomeInput } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { Disclaimer } from '../../components/Disclaimer';
import { StepIndicator } from '../../components/StepIndicator';
import { emptyInput } from '../simulation/defaults';
import { simulationInputSchema, type SimulationFormValues } from '../simulation/schema';
import { BasicInfoStep } from '../simulation/steps/BasicInfoStep';
import { CreditsStep } from '../simulation/steps/CreditsStep';
import { DeductionsStep } from '../simulation/steps/DeductionsStep';
import { DependentsStep } from '../simulation/steps/DependentsStep';
import { useRuleYears } from '../simulation/useRules';
import { GlobalPreview } from './GlobalPreview';
import { GlobalResultView } from './GlobalResultView';
import { ImportYearEndStep } from './ImportYearEndStep';
import { IncomeItemsStep } from './IncomeItemsStep';
import { emptyExtra, globalExtraSchema, type GlobalExtraValues } from './schema';
import { useGlobalCalculation } from './useGlobalCalculation';

export const GLOBAL_STEPS = [
  '연말정산 불러오기',
  '기본 정보',
  '부양가족',
  '공제',
  '사업·기타 소득',
  '결과',
] as const;

const BASE_STEP_FIELDS: Record<number, FieldPath<SimulationFormValues>[]> = {
  1: ['income', 'prepaid_tax', 'taxpayer'],
  2: ['dependents'],
  3: ['deductions', 'credits'],
};

const EARNED_ONLY_NOTE =
  '건강보험료 등 특별소득공제, 신용카드 등 소득공제, 보험료·의료비·교육비·월세 세액공제는 근로소득이 있을 때만 적용됩니다.';

type WizardProps = {
  simulationId?: number;
  initialName: string;
  initialYear: number;
  initialBase: SimulationInput;
  initialExtra: GlobalExtraValues;
  initialSourceId?: number;
  initialStep?: number;
};

function toExtra(input: StoredGlobalIncomeInput): GlobalExtraValues {
  return {
    business_incomes: input.business_incomes.map((b) => ({
      name: b.name,
      revenue: b.revenue,
      expense_method: b.expense_method,
      expenses: b.expenses,
      expense_rate: String(Number(b.expense_rate)),
      withholding_tax: b.withholding_tax ?? null,
    })),
    other_incomes: input.other_incomes.map((o) => ({
      name: o.name,
      kind: o.kind,
      revenue: o.revenue,
      expenses: o.expenses,
      withholding_tax: o.withholding_tax ?? null,
    })),
    other_income_taxation: input.other_income_taxation,
    interim_prepayment: input.interim_prepayment,
    earned_prepaid_tax: input.earned_prepaid_tax ?? null,
  };
}

function GlobalIncomeWizard({
  simulationId,
  initialName,
  initialYear,
  initialBase,
  initialExtra,
  initialSourceId,
  initialStep = 0,
}: WizardProps) {
  const years = useRuleYears();
  const [taxYear, setTaxYear] = useState(initialYear);
  const [step, setStep] = useState(initialStep);
  const [name, setName] = useState(initialName);
  const [sourceId, setSourceId] = useState<number | undefined>(initialSourceId);
  const [importedName, setImportedName] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const base = useForm<SimulationFormValues>({
    resolver: zodResolver(simulationInputSchema),
    defaultValues: initialBase,
    mode: 'onTouched',
  });
  const extra = useForm<GlobalExtraValues>({
    resolver: zodResolver(globalExtraSchema),
    defaultValues: initialExtra,
    mode: 'onTouched',
  });
  const live = useGlobalCalculation(taxYear, base, extra);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const last = GLOBAL_STEPS.length - 1;

  const changeYear = (y: number) => {
    setTaxYear(y);
    base.setValue('tax_year', y);
  };

  const importYearEnd = (sim: SimulationRead) => {
    base.reset({ ...sim.input, tax_year: taxYear });
    setSourceId(sim.id);
    setImportedName(sim.name);
    if (!simulationId) setName(`${taxYear}년 종합소득세 (${sim.name})`.slice(0, 100));
  };

  const goNext = async () => {
    let ok = true;
    const fields = BASE_STEP_FIELDS[step];
    if (fields) ok = await base.trigger(fields, { shouldFocus: true });
    if (step === 4) ok = await extra.trigger(undefined, { shouldFocus: true });
    if (ok) setStep((s) => Math.min(s + 1, last));
  };

  const save = useMutation({
    mutationFn: async () => {
      const input = live.input;
      if (!input) throw new Error('입력값에 오류가 있어 저장할 수 없습니다.');
      return simulationId
        ? api.updateGlobalSimulation(simulationId, name, input)
        : api.createGlobalSimulation(name, input, sourceId);
    },
    onSuccess: async (sim) => {
      setSaved(true);
      await queryClient.invalidateQueries({ queryKey: ['global-simulations'] });
      queryClient.setQueryData(['global-simulation', sim.id], sim);
      if (!simulationId) navigate(`/global-income/${sim.id}`, { replace: true, state: { step } });
    },
  });

  return (
    <div className="wizard">
      {simulationId ? (
        <p className="wizard__context">
          저장된 종합소득세 시뮬레이션{' '}
          <strong data-testid="global-editing-name">{initialName}</strong> 편집 중
        </p>
      ) : null}
      <StepIndicator steps={GLOBAL_STEPS} current={step} onSelect={setStep} />
      <div className={`wizard__body${step === last ? ' wizard__body--single' : ''}`}>
        <div className="wizard__main">
          <h2 className="wizard__title">{GLOBAL_STEPS[step]}</h2>

          {step === 0 ? (
            <ImportYearEndStep
              taxYear={taxYear}
              supportedYears={years.data?.supported_years ?? [taxYear]}
              onChangeYear={changeYear}
              onImport={importYearEnd}
              onStartFresh={() => setStep(1)}
              importedName={importedName}
            />
          ) : null}

          {step >= 1 && step <= 3 ? (
            <FormProvider {...base}>
              {step === 1 ? (
                <>
                  <p className="alert alert--warning">
                    근로소득이 없으면 연간 근로소득을 0원으로 두세요. 기납부세액은 「사업·기타
                    소득」 단계에서 확인합니다.
                  </p>
                  <BasicInfoStep hideTaxYear />
                </>
              ) : null}
              {step === 2 ? <DependentsStep /> : null}
              {step === 3 ? (
                <>
                  <p className="alert alert--warning">{EARNED_ONLY_NOTE}</p>
                  <DeductionsStep />
                  <CreditsStep />
                </>
              ) : null}
            </FormProvider>
          ) : null}

          {step === 4 ? (
            <FormProvider {...extra}>
              <IncomeItemsStep taxYear={taxYear} />
            </FormProvider>
          ) : null}

          {step === last ? (
            live.result ? (
              <GlobalResultView result={live.result} />
            ) : (
              <>
                <Disclaimer />
                <ApiErrorMessage error={live.error} />
                <p className="empty">
                  {live.input || live.isFetching
                    ? '계산 중…'
                    : '입력값에 오류가 있습니다. 이전 단계를 확인하세요.'}
                </p>
              </>
            )
          ) : null}

          <div className="wizard__nav">
            {step > 0 ? (
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setStep((s) => s - 1)}
              >
                <span aria-hidden="true">← </span>이전
              </button>
            ) : (
              <span />
            )}
            {step < last ? (
              <button type="button" className="btn btn--primary btn--lg" onClick={goNext}>
                다음<span aria-hidden="true"> →</span>
              </button>
            ) : null}
          </div>

          {step === last ? (
            <div className="save-panel">
              <label htmlFor="global-name">시뮬레이션 이름</label>
              <input
                id="global-name"
                value={name}
                maxLength={100}
                onChange={(e) => setName(e.target.value)}
              />
              <div className="save-panel__actions">
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={save.isPending || !name.trim() || !live.input}
                  onClick={() => {
                    setSaved(false);
                    save.mutate();
                  }}
                >
                  {simulationId ? '변경 저장' : '저장'}
                </button>
              </div>
              {saved && !save.isPending ? (
                <span className="save-panel__ok" role="status">
                  ✓ 저장되었습니다
                </span>
              ) : null}
              <ApiErrorMessage error={save.error} />
            </div>
          ) : null}
        </div>
        {step < last ? (
          <GlobalPreview
            result={live.result}
            isFetching={live.isFetching}
            inputValid={live.input !== undefined}
            error={live.error}
          />
        ) : null}
      </div>
    </div>
  );
}

/** /global-income/new (새 계산) 또는 /global-income/:id (저장본 편집). */
export function GlobalIncomePage() {
  const { id } = useParams();
  const simulationId = id ? Number(id) : undefined;
  const state = useLocation().state as { step?: number } | null;
  const years = useRuleYears();
  const loaded = useQuery({
    queryKey: ['global-simulation', simulationId],
    queryFn: () => api.getGlobalSimulation(simulationId as number),
    enabled: simulationId !== undefined,
  });

  if (simulationId !== undefined) {
    if (loaded.isPending) return <p className="empty">불러오는 중…</p>;
    if (loaded.error) return <ApiErrorMessage error={loaded.error} />;
    const sim = loaded.data;
    return (
      <GlobalIncomeWizard
        key={sim.id}
        simulationId={sim.id}
        initialName={sim.name}
        initialYear={sim.tax_year}
        initialBase={sim.input.base}
        initialExtra={toExtra(sim.input)}
        initialSourceId={sim.source_simulation_id ?? undefined}
        initialStep={state?.step ?? 5}
      />
    );
  }
  if (years.isPending) return <p className="empty">불러오는 중…</p>;
  const year = years.data?.default_tax_year ?? 2025;
  return (
    <GlobalIncomeWizard
      key="new"
      initialName={`${year}년 종합소득세`}
      initialYear={year}
      initialBase={emptyInput(year)}
      initialExtra={emptyExtra()}
    />
  );
}
