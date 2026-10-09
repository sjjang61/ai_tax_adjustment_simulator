/**
 * 저장된 개인 시뮬레이션 입력을 맞벌이 입력으로 나눈다 (입력 재배치만 수행, 세액 계산 없음).
 *
 * - 급여·기납부세액·본인 정보·공제 입력 → 해당 사람(본인/배우자)의 개인 입력
 * - 부양가족 → 「부양가족 배분」 목록 (현재 공제: 불러온 사람). 배우자 관계는 제외, 중복은 건너뜀
 * - 교육비: 대상자 이름이 부양가족 이름과 같으면 그 가족으로 옮기고, 나머지는 개인 몫에 남김
 * - 의료비: 합계만 있어 가족별로 나눌 수 없으므로 개인 몫에 남기고 안내
 */
import type { EducationExpense, SimulationInput, Spouse } from '../../api/types';
import { formatWon } from '../../lib/format';
import {
  SHARED_EDUCATION_KINDS,
  SPOUSE_LABELS,
  newSharedDependent,
  type SharedDependentFormValue,
} from './schema';

export type IndividualImport = {
  person: SimulationInput;
  added: SharedDependentFormValue[];
  notes: string[];
};

type SharedEducationKind = (typeof SHARED_EDUCATION_KINDS)[number];

function isSharedKind(kind: EducationExpense['kind']): kind is SharedEducationKind {
  return (SHARED_EDUCATION_KINDS as readonly string[]).includes(kind);
}

function sameDependent(a: SharedDependentFormValue, b: SharedDependentFormValue): boolean {
  return a.name === b.name && a.relation === b.relation && a.birth_year === b.birth_year;
}

export function importIndividual(
  source: SimulationInput,
  who: Spouse,
  existingShared: readonly SharedDependentFormValue[],
  coupleTaxYear: number,
): IndividualImport {
  const notes: string[] = [];
  const whoLabel = SPOUSE_LABELS[who];

  if (source.tax_year !== coupleTaxYear) {
    notes.push(
      `${source.tax_year}년 귀속 데이터를 ${coupleTaxYear}년 귀속 계산에 불러왔습니다. 금액을 올해 기준으로 확인하세요.`,
    );
  }

  // 1) 부양가족 → 공유 부양가족
  const candidates: SharedDependentFormValue[] = [];
  for (const dep of source.dependents) {
    if (dep.relation === 'spouse') {
      notes.push(
        `배우자${dep.name ? `(${dep.name})` : ''}는 맞벌이 입력에서 각자 입력하므로 제외했습니다.`,
      );
      continue;
    }
    candidates.push({
      ...newSharedDependent(),
      name: dep.name,
      relation: dep.relation,
      birth_year: dep.birth_year,
      disabled: dep.disabled,
      income_amount: dep.income_amount,
      income_is_salary_only: dep.income_is_salary_only,
      born_or_adopted_this_year: dep.born_or_adopted_this_year,
      child_order: dep.child_order ?? null,
      assigned_to: who,
    });
  }

  // 2) 교육비: 대상자 이름으로 가족에 연결 (같은 구분은 합산)
  const remainingEducation: EducationExpense[] = [];
  let unmatchedEducation = 0;
  for (const edu of source.credits.education) {
    const target = edu.label ? candidates.find((d) => d.name === edu.label) : undefined;
    // 가족 1명당 교육비 구분은 하나만 둘 수 있으므로, 구분이 다르면 개인 몫에 남긴다
    if (
      target &&
      isSharedKind(edu.kind) &&
      (target.education_kind == null || target.education_kind === edu.kind)
    ) {
      target.education_kind = edu.kind;
      target.education_amount += edu.amount;
      continue;
    }
    remainingEducation.push(edu);
    if (edu.kind !== 'self') unmatchedEducation += 1;
  }
  if (unmatchedEducation > 0) {
    notes.push(
      `교육비 ${unmatchedEducation}건은 대상 가족을 알 수 없어 ${whoLabel} 공제에 그대로 두었습니다. 부양가족 교육비라면 「부양가족 배분」 단계에서 가족별로 입력하세요.`,
    );
  }

  // 3) 중복 제거 후 추가
  const added: SharedDependentFormValue[] = [];
  for (const dep of candidates) {
    if ([...existingShared, ...added].some((d) => sameDependent(d, dep))) {
      notes.push(
        `${dep.name || '이름 없는 가족'}는 이미 「부양가족 배분」에 있어 추가하지 않았습니다.`,
      );
      continue;
    }
    added.push(dep);
  }
  if (added.length > 0) {
    notes.unshift(
      `부양가족 ${added.length}명을 「부양가족 배분」 단계로 옮겼습니다 (현재 공제: ${whoLabel}).`,
    );
  }

  // 4) 의료비는 가족별로 나눌 수 없음
  const m = source.credits.medical;
  const medicalTotal = m.general + m.specific + m.premature + m.infertility;
  if (source.dependents.length > 0 && medicalTotal > 0) {
    notes.push(
      `의료비 ${formatWon(medicalTotal)}은 가족별로 나눌 수 없어 ${whoLabel} 공제에 그대로 두었습니다. 부양가족 의료비라면 해당 금액을 빼고 「부양가족 배분」 단계에서 가족별로 입력하세요.`,
    );
  }

  const person: SimulationInput = {
    ...source,
    tax_year: coupleTaxYear,
    taxpayer: { ...source.taxpayer, is_married: true },
    dependents: [],
    credits: { ...source.credits, education: remainingEducation },
  };
  return { person, added, notes };
}
