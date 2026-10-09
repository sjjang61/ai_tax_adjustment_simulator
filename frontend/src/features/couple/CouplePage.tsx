import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { FormProvider, useForm, type FieldPath, type UseFormReturn } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import type { SimulationInput, SimulationRead, Spouse } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { Disclaimer } from '../../components/Disclaimer';
import { StepIndicator } from '../../components/StepIndicator';
import { emptyInput } from '../simulation/defaults';
import { simulationInputSchema, type SimulationFormValues } from '../simulation/schema';
import { BasicInfoStep } from '../simulation/steps/BasicInfoStep';
import { CreditsStep } from '../simulation/steps/CreditsStep';
import { DeductionsStep } from '../simulation/steps/DeductionsStep';
import { useRuleYears } from '../simulation/useRules';
import { CoupleAiPanel } from './CoupleAiPanel';
import { CoupleResultView } from './CoupleResultView';
import { ImportIndividualPanel } from './ImportIndividualPanel';
import { importIndividual } from './importIndividual';
import { MAX_SHARED_DEPENDENTS, sharedFormSchema, type SharedFormValues } from './schema';
import { SharedDependentsStep } from './SharedDependentsStep';
import { useCoupleOptimization } from './useCoupleOptimization';

export const COUPLE_STEPS = [
  '귀속연도',
  '본인 정보',
  '본인 공제',
  '배우자 정보',
  '배우자 공제',
  '부양가족 배분',
  '결과',
] as const;

const PERSON_STEP_FIELDS: FieldPath<SimulationFormValues>[][] = [
  ['income', 'prepaid_tax', 'taxpayer'],
  ['deductions', 'credits'],
];

function personDefaults(taxYear: number, isFemale: boolean): SimulationInput {
  const input = emptyInput(taxYear);
  return { ...input, taxpayer: { ...input.taxpayer, is_married: true, is_female: isFemale } };
}

function usePersonForm(taxYear: number, isFemale: boolean): UseFormReturn<SimulationFormValues> {
  return useForm<SimulationFormValues>({
    resolver: zodResolver(simulationInputSchema),
    defaultValues: personDefaults(taxYear, isFemale),
    mode: 'onTouched',
  });
}

const PERSONAL_NOTE =
  '부양가족의 의료비·교육비는 「부양가족 배분」 단계에서 가족별로 입력하세요. 여기에는 본인 몫(본인 의료비·교육비, 본인 카드 사용액 등)만 입력합니다.';

/** 맞벌이 부부: 부부 각자 입력 + 공유 부양가족 최적 배분 + AI 설명. */
export function CouplePage() {
  const years = useRuleYears();
  const defaultYear = years.data?.default_tax_year ?? 2025;
  const [taxYear, setTaxYear] = useState<number | null>(null);
  const year = taxYear ?? defaultYear;
  const primary = usePersonForm(year, false);
  const spouse = usePersonForm(year, true);
  const shared = useForm<SharedFormValues>({
    resolver: zodResolver(sharedFormSchema),
    defaultValues: { shared_dependents: [] },
    mode: 'onTouched',
  });
  const [step, setStep] = useState(0);
  const last = COUPLE_STEPS.length - 1;
  const live = useCoupleOptimization(year, primary, spouse, shared, step === last);
  const queryClient = useQueryClient();

  /** 저장된 개인 시뮬레이션을 본인/배우자 입력으로 불러오고 안내 문구를 돌려준다. */
  const importFor = (who: Spouse, sim: SimulationRead): string[] => {
    const form = who === 'primary' ? primary : spouse;
    const existing = shared.getValues('shared_dependents');
    const result = importIndividual(sim.input, who, existing, year);
    form.reset(result.person);
    const room = MAX_SHARED_DEPENDENTS - existing.length;
    const added = result.added.slice(0, Math.max(room, 0));
    if (added.length < result.added.length) {
      result.notes.push(
        `부양가족은 최대 ${MAX_SHARED_DEPENDENTS}명이라 ${result.added.length - added.length}명은 추가하지 못했습니다.`,
      );
    }
    shared.setValue('shared_dependents', [...existing, ...added]);
    return result.notes;
  };

  const changeYear = (next: number) => {
    setTaxYear(next);
    primary.setValue('tax_year', next);
    spouse.setValue('tax_year', next);
  };

  const goNext = async () => {
    let ok = true;
    if (step === 1 || step === 2)
      ok = await primary.trigger(PERSON_STEP_FIELDS[step - 1], { shouldFocus: true });
    if (step === 3 || step === 4)
      ok = await spouse.trigger(PERSON_STEP_FIELDS[step - 3], { shouldFocus: true });
    if (step === 5) ok = await shared.trigger(undefined, { shouldFocus: true });
    if (ok) setStep((s) => Math.min(s + 1, last));
  };

  const applyBest = () => {
    const result = live.result;
    if (!result) return;
    result.best.assignment.forEach((who, i) => {
      shared.setValue(`shared_dependents.${i}.assigned_to`, who);
    });
  };

  const saveBoth = useMutation({
    mutationFn: async () => {
      const result = live.result;
      if (!result) throw new Error('최적 배분 결과가 없습니다.');
      const p = await api.createSimulation(`${year}년 맞벌이 - 본인`, result.best_primary_input);
      const s = await api.createSimulation(`${year}년 맞벌이 - 배우자`, result.best_spouse_input);
      return [p, s] as const;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['simulations'] }),
  });

  return (
    <div className="wizard">
      <StepIndicator steps={COUPLE_STEPS} current={step} onSelect={setStep} />
      <div
        className={`wizard__body${step === last ? ' wizard__body--result' : ' wizard__body--single'}`}
      >
        <div className="wizard__main">
          <h2 className="wizard__title">{COUPLE_STEPS[step]}</h2>

          {step === 0 ? (
            <div className="step">
              <p className="step__intro">
                부부 각자의 급여·공제 정보를 입력한 뒤, 함께 부양하는 가족을 누가 공제받는 것이
                유리한지 계산합니다.
              </p>
              <div className="field" style={{ maxWidth: 240 }}>
                <label className="field__label" htmlFor="couple-tax-year">
                  귀속연도
                </label>
                <select
                  id="couple-tax-year"
                  value={year}
                  onChange={(e) => changeYear(Number(e.target.value))}
                >
                  {(years.data?.supported_years ?? [defaultYear]).map((y) => (
                    <option key={y} value={y}>
                      {y}년 귀속
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ) : null}

          {step === 1 || step === 2 ? (
            <FormProvider {...primary}>
              {step === 1 ? (
                <>
                  <ImportIndividualPanel
                    who="primary"
                    taxYear={year}
                    onImport={(sim) => importFor('primary', sim)}
                  />
                  <BasicInfoStep hideTaxYear />
                </>
              ) : (
                <>
                  <p className="alert alert--warning">{PERSONAL_NOTE}</p>
                  <DeductionsStep />
                  <CreditsStep />
                </>
              )}
            </FormProvider>
          ) : null}

          {step === 3 || step === 4 ? (
            <FormProvider {...spouse}>
              {step === 3 ? (
                <>
                  <ImportIndividualPanel
                    who="spouse"
                    taxYear={year}
                    onImport={(sim) => importFor('spouse', sim)}
                  />
                  <BasicInfoStep hideTaxYear />
                </>
              ) : (
                <>
                  <p className="alert alert--warning">{PERSONAL_NOTE}</p>
                  <DeductionsStep />
                  <CreditsStep />
                </>
              )}
            </FormProvider>
          ) : null}

          {step === 5 ? (
            <FormProvider {...shared}>
              <SharedDependentsStep taxYear={year} />
            </FormProvider>
          ) : null}

          {step === last ? (
            live.result && live.input ? (
              <>
                <CoupleResultView input={live.input} result={live.result} onApplyBest={applyBest} />
                <div className="save-panel">
                  <button
                    type="button"
                    className="btn btn--primary"
                    disabled={saveBoth.isPending}
                    onClick={() => saveBoth.mutate()}
                  >
                    추천 배분으로 각자 저장
                  </button>
                  {saveBoth.data ? (
                    <span className="save-panel__ok" role="status">
                      저장되었습니다 — <Link to={`/simulations/${saveBoth.data[0].id}`}>본인</Link>{' '}
                      · <Link to={`/simulations/${saveBoth.data[1].id}`}>배우자</Link>
                    </span>
                  ) : null}
                </div>
                <ApiErrorMessage error={saveBoth.error} />
              </>
            ) : (
              <>
                <Disclaimer />
                <ApiErrorMessage error={live.error} />
                <p className="empty">
                  {live.input || live.isFetching
                    ? '모든 배분을 계산하는 중…'
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
                onClick={() => setStep((s) => Math.max(s - 1, 0))}
              >
                <span aria-hidden="true">← </span>이전
              </button>
            ) : (
              <span />
            )}
            {step < last ? (
              <button type="button" className="btn btn--primary btn--lg" onClick={goNext}>
                {step === last - 1 ? '최적 배분 계산' : '다음'}
                <span aria-hidden="true"> →</span>
              </button>
            ) : null}
          </div>
        </div>
        {step === last ? <CoupleAiPanel input={live.input} /> : null}
      </div>
    </div>
  );
}
