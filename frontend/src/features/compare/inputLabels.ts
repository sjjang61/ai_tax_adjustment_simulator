/** 비교 화면용: 입력 경로(JSON path)를 한국어 이름으로, 값을 읽기 쉬운 문자열로 바꾼다 (표시 전용). */
import type { Dependent, EducationExpense } from '../../api/types';
import { formatWon } from '../../lib/format';
import { EDUCATION_LABELS, MORTGAGE_LABELS, RELATION_LABELS } from '../simulation/defaults';

const PATH_LABELS: Record<string, string> = {
  tax_year: '귀속연도',
  'income.annual_earned_income': '연간 근로소득',
  'income.non_taxable_income': '비과세소득',
  'prepaid_tax.withholding': '현 근무지 원천징수 소득세',
  'prepaid_tax.previous_employer': '종전 근무지 결정세액',
  'taxpayer.birth_year': '본인 출생연도',
  'taxpayer.is_female': '여성',
  'taxpayer.is_married': '배우자 있음',
  'taxpayer.is_household_head': '세대주',
  'taxpayer.disabled': '본인 장애인',
  'taxpayer.is_homeless': '무주택 세대주',
  'taxpayer.marriage_registered_this_year': '올해 혼인신고',
  'dependents[].name': '이름',
  'dependents[].relation': '관계',
  'dependents[].birth_year': '출생연도',
  'dependents[].disabled': '장애인',
  'dependents[].income_amount': '소득금액',
  'dependents[].income_is_salary_only': '근로소득만 있음',
  'dependents[].born_or_adopted_this_year': '올해 출생·입양',
  'dependents[].child_order': '출생 순서',
  'deductions.national_pension': '국민연금 등 연금보험료',
  'deductions.health_insurance': '건강보험료',
  'deductions.employment_insurance': '고용보험료',
  'deductions.housing_rent_loan_repayment': '주택임차차입금 원리금상환액',
  'deductions.long_term_mortgage_interest': '장기주택저당차입금 이자상환액',
  'deductions.mortgage_type': '장기주택저당차입금 한도 유형',
  'deductions.housing_subscription': '주택청약종합저축',
  'deductions.card.credit': '신용카드',
  'deductions.card.debit_cash': '체크카드·현금영수증',
  'deductions.card.culture': '도서·공연 등',
  'deductions.card.sports_facility': '수영장·체력단련장',
  'deductions.card.traditional_market': '전통시장',
  'deductions.card.public_transport': '대중교통',
  'deductions.venture_direct': '벤처기업 직접투자',
  'deductions.venture_fund': '벤처투자조합',
  'deductions.national_growth_fund': '국민성장펀드',
  'credits.pension_savings': '연금저축',
  'credits.irp': '퇴직연금(IRP)',
  'credits.insurance_general': '보장성보험료',
  'credits.insurance_disabled': '장애인전용 보장성보험료',
  'credits.medical.general': '의료비 (그 밖의 부양가족)',
  'credits.medical.specific': '의료비 (본인·65세 이상 등)',
  'credits.medical.premature': '의료비 (미숙아·선천성이상아)',
  'credits.medical.infertility': '의료비 (난임시술)',
  'credits.education[].kind': '구분',
  'credits.education[].amount': '금액',
  'credits.education[].label': '대상자',
  'credits.donations.political': '정치자금기부금',
  'credits.donations.hometown': '고향사랑기부금',
  'credits.donations.hometown_disaster': '고향사랑기부금 (특별재난지역)',
  'credits.donations.special': '특례기부금',
  'credits.donations.general': '일반기부금',
  'credits.donations.religious': '일반기부금 (종교단체)',
  'credits.monthly_rent': '월세',
};

const LIST_LABELS: Record<string, string> = {
  dependents: '부양가족',
  'credits.education': '교육비',
};
const PLAIN_NUMBER_FIELDS = new Set(['tax_year', 'birth_year', 'child_order']);

/** "dependents[1].birth_year" → "부양가족 2 · 출생연도" */
export function describePath(path: string): string {
  const match = /^(.*?)\[(\d+)\](?:\.(.+))?$/.exec(path);
  if (!match) return PATH_LABELS[path] ?? path;
  const [, list = '', index = '0', rest] = match;
  const head = `${LIST_LABELS[list] ?? list} ${Number(index) + 1}`;
  if (!rest) return head;
  return `${head} · ${PATH_LABELS[`${list}[].${rest}`] ?? rest}`;
}

function isDependent(value: object): value is Dependent {
  return 'relation' in value && 'birth_year' in value;
}

function isEducation(value: object): value is EducationExpense {
  return 'kind' in value && 'amount' in value;
}

/** 경로에 맞게 값을 표시한다. null = 없음(추가·삭제된 항목). */
export function formatInputValue(path: string, value: unknown): string {
  if (value === null || value === undefined) return '없음';
  if (typeof value === 'boolean') return value ? '예' : '아니오';
  const leaf = path.split('.').at(-1) ?? path;
  if (typeof value === 'number') {
    return PLAIN_NUMBER_FIELDS.has(leaf) ? String(value) : formatWon(value);
  }
  if (typeof value === 'string') {
    if (value === '') return '(빈 값)';
    if (leaf === 'relation') return RELATION_LABELS[value as Dependent['relation']] ?? value;
    if (leaf === 'kind') return EDUCATION_LABELS[value as EducationExpense['kind']] ?? value;
    if (leaf === 'mortgage_type') {
      return MORTGAGE_LABELS[value as keyof typeof MORTGAGE_LABELS] ?? value;
    }
    return value;
  }
  if (typeof value === 'object') {
    if (isDependent(value)) {
      const name = value.name ? `${value.name} ` : '';
      return `${name}(${RELATION_LABELS[value.relation]}, ${value.birth_year}년생)`;
    }
    if (isEducation(value)) return `${EDUCATION_LABELS[value.kind]} ${formatWon(value.amount)}`;
  }
  return JSON.stringify(value);
}

/** 차이 금액 표시: +1,000원 / −1,000원 / 0원 */
export function formatDelta(value: number): string {
  if (value === 0) return '0원';
  return `${value > 0 ? '+' : '−'}${formatWon(Math.abs(value))}`;
}
