import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { api } from '../../api/client';
import type { PartnerResult } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { Disclaimer } from '../../components/Disclaimer';
import { describeBalance, formatWon } from '../../lib/format';
import { GlobalResultView } from '../global/GlobalResultView';
import { AllocationTable } from './AllocationTable';

function balanceText(value: number): string {
  const b = describeBalance(value);
  if (b.kind === 'none') return '0원';
  return `${b.kind === 'payment' ? '납부' : b.label} ${formatWon(b.amount)}`;
}

function PartnerCard({ p }: { p: PartnerResult }) {
  const r = p.result;
  const b = describeBalance(r.total_balance_due);
  return (
    <article className={`partner-card summary--${b.kind}`} aria-label={`${p.partner.name} 결과`}>
      <header className="partner-card__head">
        <strong>{p.partner.name}</strong>
        <span className="tag">지분 {p.partner.ratio}</span>
      </header>
      <p className="partner-card__amount" data-testid="partner-total">
        {balanceText(r.total_balance_due)}
      </p>
      <dl className="partner-card__list">
        <div>
          <dt>연말정산 결과</dt>
          <dd>{p.simulation_name ?? '연결 안 됨'}</dd>
        </div>
        <div>
          <dt>근로소득금액</dt>
          <dd>{formatWon(r.earned_income_amount)}</dd>
        </div>
        <div>
          <dt>사업소득금액 (지분)</dt>
          <dd>{formatWon(r.business_income_amount)}</dd>
        </div>
        <div>
          <dt>종합소득금액</dt>
          <dd>{formatWon(r.comprehensive_income_amount)}</dd>
        </div>
        <div>
          <dt>결정세액</dt>
          <dd>{formatWon(r.tax_result.determined_tax)}</dd>
        </div>
        <div>
          <dt>기납부세액</dt>
          <dd>{formatWon(r.prepaid.total)}</dd>
        </div>
      </dl>
      {p.notes.length > 0 ? (
        <ul className="partner-card__notes">
          {p.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

/** 공동대표 일괄 종합소득세 계산: 각자의 연말정산 결과 + 지분만큼의 사업소득. */
export function PartnershipPage() {
  const businessId = Number(useParams().id);
  const queryClient = useQueryClient();
  const business = useQuery({
    queryKey: ['business', businessId],
    queryFn: () => api.getBusiness(businessId),
  });
  const result = useQuery({
    queryKey: ['partnership', businessId, business.data?.updated_at],
    queryFn: () => {
      if (!business.data) throw new Error('사업자 정보가 없습니다.');
      return api.calculatePartnership(business.data.record);
    },
    enabled: business.data !== undefined,
  });
  const saveAll = useMutation({
    mutationFn: async () => {
      const data = result.data;
      const b = business.data;
      if (!data || !b) throw new Error('계산 결과가 없습니다.');
      const saved = [];
      for (const p of data.partners) {
        saved.push(
          await api.createGlobalSimulation(
            `${b.tax_year}년 종합소득세 - ${p.partner.name} (${b.name})`.slice(0, 100),
            p.input,
            p.partner.simulation_id ?? undefined,
          ),
        );
      }
      return saved;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['global-simulations'] }),
  });

  const error = business.error ?? result.error;
  const data = result.data;
  return (
    <div className="result partnership">
      <header className="panel__header">
        <h2>공동대표 일괄 종합소득세{business.data ? ` — ${business.data.name}` : ''}</h2>
        <Link to={`/global-income/businesses/${businessId}`} className="btn btn--ghost btn--small">
          사업자 정보로
        </Link>
      </header>
      <ApiErrorMessage error={error} />
      {!data ? (
        !error ? (
          <p className="empty">계산하는 중…</p>
        ) : null
      ) : (
        <>
          <section
            className={`summary summary--${describeBalance(data.combined_total_balance_due).kind}`}
            aria-label="공동대표 합계"
          >
            <p className="summary__label">
              공동대표 {data.partners.length}명 합계 <small>(지방소득세 포함)</small>
            </p>
            <p className="summary__amount" data-testid="partnership-total">
              {balanceText(data.combined_total_balance_due)}
            </p>
          </section>
          <Disclaimer text={data.partners[0]?.result.disclaimer} />
          <AllocationTable allocation={data.allocation} />
          <div className="partner-cards">
            {data.partners.map((p, i) => (
              <PartnerCard key={i} p={p} />
            ))}
          </div>
          {data.partners.map((p, i) => (
            <details key={i} className="couple-detail">
              <summary>{p.partner.name} 상세 계산</summary>
              <GlobalResultView result={p.result} />
            </details>
          ))}
          <div className="save-panel">
            <div className="save-panel__actions">
              <button
                type="button"
                className="btn btn--primary"
                disabled={saveAll.isPending}
                onClick={() => saveAll.mutate()}
              >
                대표별 종합소득세로 각각 저장
              </button>
            </div>
            {saveAll.data ? (
              <span className="save-panel__ok" role="status">
                ✓ {saveAll.data.length}건 저장되었습니다 —{' '}
                {saveAll.data.map((s, i) => (
                  <span key={s.id}>
                    {i > 0 ? ' · ' : ''}
                    <Link to={`/global-income/${s.id}`}>{data.partners[i]?.partner.name}</Link>
                  </span>
                ))}
              </span>
            ) : null}
            <ApiErrorMessage error={saveAll.error} />
          </div>
        </>
      )}
    </div>
  );
}
