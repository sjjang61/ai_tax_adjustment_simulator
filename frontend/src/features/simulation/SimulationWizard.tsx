import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { FormProvider, useForm, type FieldPath } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import type { SimulationInput, SimulationRead } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { Disclaimer } from '../../components/Disclaimer';
import { StepIndicator } from '../../components/StepIndicator';
import { ComparisonView } from '../compare/ComparisonView';
import { useComparison } from '../compare/useComparison';
import { AiRecommendations } from '../result/AiRecommendations';
import { ResultView } from '../result/ResultView';
import { LivePreview } from './LivePreview';
import { simulationInputSchema, type SimulationFormValues } from './schema';
import { BasicInfoStep } from './steps/BasicInfoStep';
import { CreditsStep } from './steps/CreditsStep';
import { DeductionsStep } from './steps/DeductionsStep';
import { DependentsStep } from './steps/DependentsStep';
import { useLiveCalculation } from './useLiveCalculation';

export const STEPS = ['기본 정보', '인적공제', '소득공제', '세액공제', '결과'] as const;

const STEP_FIELDS: FieldPath<SimulationFormValues>[][] = [
  ['tax_year', 'income', 'prepaid_tax', 'taxpayer'],
  ['dependents'],
  ['deductions'],
  ['credits'],
  [],
];

type SimulationWizardProps = {
  initialInput: SimulationInput;
  initialName?: string;
  simulationId?: number;
  initialStep?: number;
};

export function SimulationWizard({
  initialInput,
  initialName,
  simulationId,
  initialStep = 0,
}: SimulationWizardProps) {
  const methods = useForm<SimulationFormValues>({
    resolver: zodResolver(simulationInputSchema),
    defaultValues: initialInput,
    mode: 'onTouched',
  });
  const [step, setStep] = useState(initialStep);
  const [name, setName] = useState(initialName ?? `${initialInput.tax_year}년 시뮬레이션`);
  const [saved, setSaved] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const live = useLiveCalculation(methods.control);
  const comparison = useComparison(simulationId, live.input);
  const [resultTab, setResultTab] = useState<'result' | 'compare'>('result');
  const changedCount = comparison.data?.comparison.input_diffs.length ?? 0;

  const save = useMutation({
    mutationFn: (values: SimulationFormValues): Promise<SimulationRead> =>
      simulationId
        ? api.updateSimulation(simulationId, name, values)
        : api.createSimulation(name, values),
    onSuccess: async (sim) => {
      setSaved(true);
      await queryClient.invalidateQueries({ queryKey: ['simulations'] });
      // 저장본이 바뀌었으므로 비교 기준도 다시 계산한다
      await queryClient.invalidateQueries({ queryKey: ['compare', sim.id] });
      queryClient.setQueryData(['simulation', sim.id], sim);
      if (!simulationId) navigate(`/simulations/${sim.id}`, { replace: true, state: { step } });
    },
  });

  const saveAsNew = useMutation({
    mutationFn: (values: SimulationFormValues) => api.createSimulation(name, values),
    onSuccess: async (sim) => {
      await queryClient.invalidateQueries({ queryKey: ['simulations'] });
      queryClient.setQueryData(['simulation', sim.id], sim);
      navigate(`/simulations/${sim.id}`, { state: { step } });
    },
  });

  const goNext = async () => {
    const fields = STEP_FIELDS[step] ?? [];
    const ok = fields.length === 0 || (await methods.trigger(fields, { shouldFocus: true }));
    if (ok) setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };
  const goPrev = () => setStep((s) => Math.max(s - 1, 0));

  const onSubmit = methods.handleSubmit((values) => {
    setSaved(false);
    save.mutate(values);
  });

  return (
    <FormProvider {...methods}>
      <form className="wizard" onSubmit={onSubmit} noValidate>
        {simulationId ? (
          <p className="wizard__context">
            저장된 시뮬레이션 <strong data-testid="editing-name">{initialName}</strong> 편집 중
          </p>
        ) : null}
        <StepIndicator steps={STEPS} current={step} onSelect={setStep} />
        <div className={`wizard__body${step === STEPS.length - 1 ? ' wizard__body--result' : ''}`}>
          <div className="wizard__main">
            <h2 className="wizard__title">{STEPS[step]}</h2>
            {step === 0 ? <BasicInfoStep /> : null}
            {step === 1 ? <DependentsStep /> : null}
            {step === 2 ? <DeductionsStep /> : null}
            {step === 3 ? <CreditsStep /> : null}
            {step === 4 && simulationId ? (
              <div className="tabs" role="tablist" aria-label="결과 보기">
                <button
                  type="button"
                  role="tab"
                  aria-selected={resultTab === 'result'}
                  className="tabs__tab"
                  onClick={() => setResultTab('result')}
                >
                  현재 결과
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={resultTab === 'compare'}
                  className="tabs__tab"
                  onClick={() => setResultTab('compare')}
                >
                  저장본과 비교{changedCount ? ` (${changedCount}개 변경)` : ''}
                </button>
              </div>
            ) : null}
            {step === 4 && simulationId && resultTab === 'compare' ? (
              comparison.data ? (
                <ComparisonView data={comparison.data} />
              ) : (
                <>
                  <ApiErrorMessage error={comparison.error} />
                  <p className="empty">비교하는 중…</p>
                </>
              )
            ) : step === 4 ? (
              live.result ? (
                <ResultView result={live.result} />
              ) : (
                <>
                  <Disclaimer />
                  <p className="empty">
                    {live.inputValid
                      ? '계산 중…'
                      : '입력값에 오류가 있습니다. 이전 단계를 확인하세요.'}
                  </p>
                </>
              )
            ) : null}

            <div className="wizard__nav">
              {step > 0 ? (
                <button type="button" className="btn btn--ghost" onClick={goPrev}>
                  <span aria-hidden="true">← </span>이전
                </button>
              ) : (
                <span />
              )}
              {step < STEPS.length - 1 ? (
                <button type="button" className="btn btn--primary btn--lg" onClick={goNext}>
                  다음<span aria-hidden="true"> →</span>
                </button>
              ) : null}
            </div>

            {step === STEPS.length - 1 ? (
              <div className="save-panel">
                <label htmlFor="simulation-name">시뮬레이션 이름</label>
                <input
                  id="simulation-name"
                  value={name}
                  maxLength={100}
                  onChange={(e) => setName(e.target.value)}
                />
                <div className="save-panel__actions">
                  <button
                    type="submit"
                    className="btn btn--primary"
                    disabled={save.isPending || !name.trim()}
                  >
                    {simulationId ? '변경 저장' : '저장'}
                  </button>
                  {simulationId ? (
                    <button
                      type="button"
                      className="btn btn--secondary"
                      disabled={saveAsNew.isPending || !name.trim()}
                      onClick={methods.handleSubmit((values) => saveAsNew.mutate(values))}
                    >
                      새 항목으로 저장
                    </button>
                  ) : null}
                </div>
                {saved && !save.isPending ? (
                  <span className="save-panel__ok" role="status">
                    ✓ 저장되었습니다
                  </span>
                ) : null}
              </div>
            ) : null}
            <ApiErrorMessage error={save.error ?? saveAsNew.error} />
          </div>
          {step < STEPS.length - 1 ? (
            <LivePreview
              result={live.result}
              isFetching={live.isFetching}
              inputValid={live.inputValid}
              error={live.error}
              comparison={
                simulationId && comparison.data
                  ? { saving: comparison.data.comparison.saving, changedCount }
                  : undefined
              }
            />
          ) : (
            <AiRecommendations
              input={live.input}
              onApply={(input) => methods.reset(input, { keepDefaultValues: true })}
            />
          )}
        </div>
      </form>
    </FormProvider>
  );
}
