import { zodResolver } from '@hookform/resolvers/zod';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useFieldArray, useForm, useWatch } from 'react-hook-form';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../../api/client';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { ControlledMoneyField } from '../../components/ControlledMoneyField';
import { Field } from '../../components/Field';
import { OptionalMoneyField } from '../../components/OptionalMoneyField';
import { useDebouncedValue } from '../../lib/useDebouncedValue';
import { useRuleYears } from '../simulation/useRules';
import { AllocationTable } from './AllocationTable';
import {
  MAX_PARTNERS,
  businessFormSchema,
  emptyBusiness,
  toBusinessForm,
  type BusinessFormValues,
} from './schema';

function BusinessForm({
  businessId,
  initial,
}: {
  businessId?: number;
  initial: BusinessFormValues;
}) {
  const years = useRuleYears();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const form = useForm<BusinessFormValues>({
    resolver: zodResolver(businessFormSchema),
    defaultValues: initial,
    mode: 'onTouched',
  });
  const { control, register, setValue, formState, handleSubmit } = form;
  const partners = useFieldArray({ control, name: 'partners' });
  const taxYear = useWatch({ control, name: 'tax_year' });
  const method = useWatch({ control, name: 'expense_method' });

  // 연결할 수 있는 연말정산 시뮬레이션 (같은 귀속연도)
  const sims = useQuery({
    queryKey: ['simulations', String(taxYear)],
    queryFn: () => api.listSimulations(taxYear),
  });

  // 배분 미리보기 (백엔드 계산)
  const values = form.watch();
  const serialized = JSON.stringify(values);
  const debounced = useDebouncedValue(serialized, 300);
  const parsed = useMemo(() => businessFormSchema.safeParse(JSON.parse(debounced)), [debounced]);
  const allocation = useQuery({
    queryKey: ['business-allocate', debounced],
    queryFn: () => api.allocateBusiness(parsed.data as BusinessFormValues),
    enabled: parsed.success && debounced === serialized,
    placeholderData: keepPreviousData,
  });

  const save = useMutation({
    mutationFn: (v: BusinessFormValues) =>
      businessId ? api.updateBusiness(businessId, v) : api.createBusiness(v),
    onSuccess: async (b) => {
      setSaved(true);
      await queryClient.invalidateQueries({ queryKey: ['businesses'] });
      queryClient.setQueryData(['business', b.id], b);
      if (!businessId) navigate(`/global-income/businesses/${b.id}`, { replace: true });
    },
  });

  const errors = formState.errors;
  return (
    <form
      className="panel business-form"
      aria-label="사업자 정보"
      noValidate
      onSubmit={handleSubmit((v) => {
        setSaved(false);
        save.mutate(v);
      })}
    >
      <header className="panel__header">
        <h2>{businessId ? '사업자 수정' : '사업자 등록'}</h2>
        <Link to="/global-income/businesses" className="btn btn--ghost btn--small">
          목록으로
        </Link>
      </header>

      <fieldset className="section">
        <legend className="section__title">사업장</legend>
        <div className="section__grid">
          <Field id="biz-name" label="사업장 이름" error={errors.name?.message}>
            <input id="biz-name" placeholder="예: 공동 스튜디오" {...register('name')} />
          </Field>
          <div className="field">
            <label className="field__label" htmlFor="biz-year">
              귀속연도
            </label>
            <select id="biz-year" {...register('tax_year', { valueAsNumber: true })}>
              {(years.data?.supported_years ?? [taxYear]).map((y) => (
                <option key={y} value={y}>
                  {y}년 귀속
                </option>
              ))}
            </select>
          </div>
          <ControlledMoneyField control={control} name="revenue" label="총수입금액 (사업장 전체)" />
          <div className="field">
            <label className="field__label" htmlFor="biz-method">
              필요경비 계산 방법
            </label>
            <select id="biz-method" {...register('expense_method')}>
              <option value="book">장부 (실제 경비)</option>
              <option value="rate">경비율 (단순·기준경비율)</option>
            </select>
          </div>
          {method === 'rate' ? (
            <Field
              id="biz-rate"
              label="경비율 (%)"
              hint="홈택스 「기준·단순경비율 조회」에서 업종코드로 확인하세요"
              error={errors.expense_rate?.message}
            >
              <input id="biz-rate" inputMode="decimal" {...register('expense_rate')} />
            </Field>
          ) : (
            <ControlledMoneyField
              control={control}
              name="expenses"
              label="필요경비 (사업장 전체)"
            />
          )}
        </div>
        <OptionalMoneyField
          control={control}
          setValue={setValue}
          name="withholding_tax"
          autoHint="비워 두면 총수입금액의 원천징수세율(사업소득)만큼 원천징수된 것으로 계산합니다."
          fieldLabel="원천징수된 소득세 (사업장 전체)"
        />
      </fieldset>

      <fieldset className="section">
        <legend className="section__title">대표자 · 손익분배비율</legend>
        <p className="section__note">
          지분은 비율로 입력합니다 (예: 5:5 → 5와 5, 6:4 → 6과 4). 각 대표의 연말정산 결과를
          연결하면 공동대표 일괄 계산 때 근로소득을 함께 반영합니다.
        </p>
        {partners.fields.map((f, i) => {
          const pe = errors.partners?.[i];
          return (
            <div key={f.id} className="row partner-row">
              <Field id={`p-${i}-name`} label={`대표자 ${i + 1}`} error={pe?.name?.message}>
                <input id={`p-${i}-name`} placeholder="이름" {...register(`partners.${i}.name`)} />
              </Field>
              <Field id={`p-${i}-share`} label="지분" error={pe?.share?.message}>
                <input
                  id={`p-${i}-share`}
                  type="number"
                  min={1}
                  {...register(`partners.${i}.share`, {
                    setValueAs: (v: unknown) => (v === '' || v == null ? Number.NaN : Number(v)),
                  })}
                />
              </Field>
              <Field
                id={`p-${i}-sim`}
                label="연말정산 결과 연결"
                error={pe?.simulation_id?.message}
              >
                <select
                  id={`p-${i}-sim`}
                  {...register(`partners.${i}.simulation_id`, {
                    setValueAs: (v: unknown) => (v === '' || v == null ? null : Number(v)),
                  })}
                >
                  <option value="">연결 안 함 (근로소득 없음)</option>
                  {sims.data?.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </Field>
              <button
                type="button"
                className="btn btn--ghost btn--small"
                disabled={partners.fields.length <= 1}
                onClick={() => partners.remove(i)}
                aria-label={`대표자 ${i + 1} 삭제`}
              >
                삭제
              </button>
            </div>
          );
        })}
        <button
          type="button"
          className="btn btn--secondary"
          disabled={partners.fields.length >= MAX_PARTNERS}
          onClick={() => partners.append({ name: '', share: 1, simulation_id: null })}
        >
          + 대표자 추가
        </button>
        {errors.partners?.root?.message || errors.partners?.message ? (
          <p className="field__error" role="alert">
            {errors.partners?.root?.message ?? errors.partners?.message}
          </p>
        ) : null}
      </fieldset>

      {allocation.data ? (
        <AllocationTable allocation={allocation.data} />
      ) : (
        <p className="empty">입력을 확인하면 지분별 배분이 표시됩니다.</p>
      )}
      <ApiErrorMessage error={allocation.error} />

      <div className="save-panel">
        <div className="save-panel__actions">
          <button type="submit" className="btn btn--primary" disabled={save.isPending}>
            {businessId ? '변경 저장' : '저장'}
          </button>
          {businessId ? (
            <Link
              to={`/global-income/businesses/${businessId}/partnership`}
              className="btn btn--secondary"
            >
              공동대표 일괄 종합소득세 계산
            </Link>
          ) : null}
        </div>
        {saved && !save.isPending ? (
          <span className="save-panel__ok" role="status">
            ✓ 저장되었습니다
          </span>
        ) : null}
        <ApiErrorMessage error={save.error} />
      </div>
    </form>
  );
}

/** /global-income/businesses/new 또는 /global-income/businesses/:id */
export function BusinessFormPage() {
  const { id } = useParams();
  const businessId = id ? Number(id) : undefined;
  const years = useRuleYears();
  const loaded = useQuery({
    queryKey: ['business', businessId],
    queryFn: () => api.getBusiness(businessId as number),
    enabled: businessId !== undefined,
  });
  if (businessId !== undefined) {
    if (loaded.isPending) return <p className="empty">불러오는 중…</p>;
    if (loaded.error) return <ApiErrorMessage error={loaded.error} />;
    return (
      <BusinessForm
        key={loaded.data.id}
        businessId={loaded.data.id}
        initial={toBusinessForm(loaded.data.record)}
      />
    );
  }
  if (years.isPending) return <p className="empty">불러오는 중…</p>;
  return <BusinessForm key="new" initial={emptyBusiness(years.data?.default_tax_year ?? 2025)} />;
}
