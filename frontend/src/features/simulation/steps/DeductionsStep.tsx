import { useFormContext, useWatch } from 'react-hook-form';
import { formatRate, formatWon } from '../../../lib/format';
import { MORTGAGE_LABELS } from '../defaults';
import { MoneyField, Section } from '../fields';
import { MORTGAGE_TYPES, type SimulationFormValues } from '../schema';
import { useRules } from '../useRules';

export function DeductionsStep() {
  const { control, register } = useFormContext<SimulationFormValues>();
  const taxYear = useWatch({ control, name: 'tax_year' });
  const rules = useRules(taxYear).data;
  const card = rules?.card;
  const housing = rules?.housing;

  return (
    <div className="step">
      <Section title="연금·보험료">
        <MoneyField
          name="deductions.national_pension"
          label="국민연금 등 연금보험료"
          hint="근로자 부담분 전액 공제"
        />
        <MoneyField name="deductions.health_insurance" label="건강보험료 (장기요양 포함)" />
        <MoneyField name="deductions.employment_insurance" label="고용보험료" />
      </Section>

      <Section
        title="주택자금 · 주택청약"
        note={
          housing
            ? `주택임차차입금·주택청약 합산 ${formatWon(housing.rent_loan_and_subscription_limit)} 한도, 무주택 세대주 요건`
            : undefined
        }
      >
        <MoneyField
          name="deductions.housing_rent_loan_repayment"
          label="주택임차차입금 원리금상환액"
          hint={housing ? `상환액의 ${formatRate(housing.rent_loan_rate)}` : undefined}
        />
        <MoneyField
          name="deductions.long_term_mortgage_interest"
          label="장기주택저당차입금 이자상환액"
        />
        <div className="field">
          <label className="field__label" htmlFor="f-deductions-mortgage_type">
            장기주택저당차입금 한도 유형
          </label>
          <select
            id="f-deductions-mortgage_type"
            {...register('deductions.mortgage_type', {
              setValueAs: (v: unknown) => (v === '' || v === null ? null : v),
            })}
          >
            <option value="">선택 안 함</option>
            {MORTGAGE_TYPES.map((t) => (
              <option key={t} value={t}>
                {MORTGAGE_LABELS[t]}
                {housing ? ` (한도 ${formatWon(housing.mortgage_limits[t] ?? 0)})` : ''}
              </option>
            ))}
          </select>
        </div>
        <MoneyField
          name="deductions.housing_subscription"
          label="주택청약종합저축 납입액"
          hint={
            housing
              ? `연 ${formatWon(housing.subscription_payment_limit)} 한도 × ${formatRate(housing.subscription_rate)}, 총급여 ${formatWon(housing.subscription_gross_salary_limit)} 이하`
              : undefined
          }
        />
      </Section>

      <Section
        title="신용카드 등 사용액"
        note={
          card
            ? `총급여의 ${formatRate(card.minimum_usage_rate)}를 초과한 사용분부터 공제됩니다.`
            : undefined
        }
      >
        <MoneyField
          name="deductions.card.credit"
          label="신용카드"
          hint={card ? `공제율 ${formatRate(card.credit_rate)}` : undefined}
        />
        <MoneyField
          name="deductions.card.debit_cash"
          label="체크카드·현금영수증"
          hint={card ? `공제율 ${formatRate(card.debit_cash_rate)}` : undefined}
        />
        <MoneyField
          name="deductions.card.culture"
          label="도서·공연·박물관·미술관·영화"
          hint={
            card
              ? `공제율 ${formatRate(card.culture_rate)} (총급여 ${formatWon(card.culture_gross_salary_limit)} 이하)`
              : undefined
          }
        />
        <MoneyField
          name="deductions.card.sports_facility"
          label="수영장·체력단련장 시설이용료"
          hint={card ? `공제율 ${formatRate(card.sports_facility_rate)}` : undefined}
        />
        <MoneyField
          name="deductions.card.traditional_market"
          label="전통시장"
          hint={card ? `공제율 ${formatRate(card.traditional_market_rate)}` : undefined}
        />
        <MoneyField
          name="deductions.card.public_transport"
          label="대중교통"
          hint={card ? `공제율 ${formatRate(card.public_transport_rate)}` : undefined}
        />
      </Section>

      <Section title="벤처투자 등">
        <MoneyField name="deductions.venture_direct" label="벤처기업 등 직접 투자" />
        <MoneyField
          name="deductions.venture_fund"
          label="벤처투자조합 등 간접 투자"
          hint={rules ? `투자액의 ${formatRate(rules.venture.fund_rate)}` : undefined}
        />
      </Section>

      {rules?.national_growth_fund ? (
        <Section
          title="국민성장펀드"
          note={`전용계좌로 ${rules.national_growth_fund.min_holding_years}년 이상 보유해야 하며, 그 전에 환매하면 감면세액이 추징될 수 있습니다.`}
        >
          <MoneyField
            name="deductions.national_growth_fund"
            label="국민성장펀드 납입액"
            hint={`${rules.national_growth_fund.tiers
              .filter((t) => t.upper != null && Number(t.rate) > 0) // 공제율 0% 구간은 안내 생략
              .map((t) => `${formatWon(t.upper ?? 0)} 이하 ${formatRate(t.rate)}`)
              .join(', ')} (최대 ${formatWon(rules.national_growth_fund.max_deduction)})`}
          />
        </Section>
      ) : null}
    </div>
  );
}
