import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import type { PartnerShare } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { formatWon } from '../../lib/format';

type BusinessImportPanelProps = {
  taxYear: number;
  /** 선택한 대표자의 지분만큼의 사업소득을 추가한다. */
  onImport: (share: PartnerShare, businessName: string) => void;
};

/** 종합소득세 입력: 사업자 소득관리에서 본인 지분만큼의 사업소득 불러오기. */
export function BusinessImportPanel({ taxYear, onImport }: BusinessImportPanelProps) {
  const [businessId, setBusinessId] = useState('');
  const [partnerIndex, setPartnerIndex] = useState('');
  const [done, setDone] = useState<string | null>(null);
  const list = useQuery({
    queryKey: ['businesses', String(taxYear)],
    queryFn: () => api.listBusinesses(taxYear),
  });
  const business = useQuery({
    queryKey: ['business', Number(businessId)],
    queryFn: () => api.getBusiness(Number(businessId)),
    enabled: businessId !== '',
  });
  const partners = business.data?.allocation.partners ?? [];

  return (
    <section className="import-individual" aria-label="사업자 관리에서 불러오기">
      <div className="import-individual__head">
        <strong>🏢 사업자 소득관리에서 불러오기</strong>
        <Link to="/global-income/businesses" className="import-individual__all">
          사업자 관리 →
        </Link>
      </div>
      {list.isPending ? (
        <p className="preview__hint">불러오는 중…</p>
      ) : (list.data ?? []).length === 0 ? (
        <p className="preview__hint">
          {taxYear}년 귀속으로 등록된 사업자가 없습니다. 「사업자 관리」에서 등록하거나 아래에 직접
          입력하세요.
        </p>
      ) : (
        <div className="import-individual__row">
          <select
            aria-label="사업자 선택"
            value={businessId}
            onChange={(e) => {
              setBusinessId(e.target.value);
              setPartnerIndex('');
              setDone(null);
            }}
          >
            <option value="">사업자 선택</option>
            {list.data?.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name} (소득금액 {formatWon(b.income_amount)}
                {b.partner_count > 1 ? `, 공동대표 ${b.partner_count}인` : ''})
              </option>
            ))}
          </select>
          <select
            aria-label="본인 대표자 선택"
            value={partnerIndex}
            disabled={partners.length === 0}
            onChange={(e) => setPartnerIndex(e.target.value)}
          >
            <option value="">대표자(본인) 선택</option>
            {partners.map((p, i) => (
              <option key={i} value={i}>
                {p.name} (지분 {p.ratio}, 소득금액 {formatWon(p.income_amount)})
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn--secondary btn--small"
            disabled={partnerIndex === '' || !business.data}
            onClick={() => {
              const share = partners[Number(partnerIndex)];
              if (!share || !business.data) return;
              onImport(share, business.data.name);
              setDone(
                `${business.data.name}의 ${share.name} 지분(${share.ratio})을 사업소득으로 추가했습니다.`,
              );
            }}
          >
            지분만큼 불러오기
          </button>
        </div>
      )}
      <ApiErrorMessage error={list.error ?? business.error} />
      {done ? (
        <div className="import-individual__done" role="status">
          <p>✓ {done}</p>
        </div>
      ) : null}
    </section>
  );
}
