/**
 * OpenAPI 스키마(백엔드)에서 생성된 타입의 별칭.
 * 타입을 수동으로 복제하지 않는다 — 스키마가 바뀌면 `npm run gen:api`로 재생성한다.
 */
import type { components } from './schema';

type Schemas = components['schemas'];

export type SimulationInput = Schemas['SimulationInput'];
export type Dependent = Schemas['Dependent'];
export type Relation = Schemas['Relation'];
export type EducationExpense = Schemas['EducationExpense'];
export type EducationKind = Schemas['EducationKind'];
export type MortgageType = Schemas['MortgageType'];
export type TaxResult = Schemas['TaxResult'];
export type BreakdownItem = Schemas['BreakdownItem'];
export type CalcWarning = Schemas['CalcWarning'];
export type MethodComparison = Schemas['MethodComparison'];
export type CreditMethod = Schemas['CreditMethod'];
export type SimulationRead = Schemas['SimulationRead'];
export type SimulationSummary = Schemas['SimulationSummary'];
export type SimulationWithWarnings = Schemas['SimulationWithWarnings'];
export type SimulationExport = Schemas['SimulationExport'];
export type TaxRules = Schemas['TaxRules'];
export type RulesYears = Schemas['RulesYears'];
export type ErrorResponse = Schemas['ErrorResponse'];
export type RecommendationResponse = Schemas['RecommendationResponse'];
export type Recommendation = Schemas['Recommendation'];
export type RecommendationCategory = Schemas['RecommendationCategory'];
export type CoupleInput = Schemas['CoupleInput'];
export type SharedDependent = Schemas['SharedDependent'];
export type Spouse = Schemas['Spouse'];
export type PlanSummary = Schemas['PlanSummary'];
export type CoupleOptimizationResult = Schemas['CoupleOptimizationResult'];
export type CoupleRecommendationResponse = Schemas['CoupleRecommendationResponse'];
export type SimulationComparison = Schemas['SimulationComparison'];
export type ComparisonResult = Schemas['ComparisonResult'];
export type MetricDiff = Schemas['MetricDiff'];
export type ItemDiff = Schemas['ItemDiff'];
export type InputDiff = Schemas['InputDiff'];
/** 요청용 (경비율은 숫자 또는 문자열) */
export type GlobalIncomeInput = Schemas['GlobalIncomeInput-Input'];
/** 저장된 입력(응답) — 경비율은 문자열 */
export type StoredGlobalIncomeInput = Schemas['GlobalIncomeInput-Output'];
export type GlobalIncomeResult = Schemas['GlobalIncomeResult'];
export type BusinessIncome = Schemas['BusinessIncome-Input'];
export type OtherIncome = Schemas['OtherIncome'];
export type IncomeLine = Schemas['IncomeLine'];
export type TaxationOption = Schemas['TaxationOption'];
export type GlobalIncomeSimulationRead = Schemas['GlobalIncomeSimulationRead'];
export type GlobalIncomeSimulationSummary = Schemas['GlobalIncomeSimulationSummary'];
/** 사업자 소득관리 — 요청용 레코드 (경비율 숫자 또는 문자열) */
export type BusinessRecord = Schemas['BusinessRecord-Input'];
export type StoredBusinessRecord = Schemas['BusinessRecord-Output'];
export type Partner = Schemas['Partner'];
export type PartnerShare = Schemas['PartnerShare'];
export type BusinessAllocation = Schemas['BusinessAllocation'];
export type BusinessRead = Schemas['BusinessRead'];
export type BusinessSummary = Schemas['BusinessSummary'];
export type PartnershipResult = Schemas['PartnershipResult'];
export type PartnerResult = Schemas['PartnerResult'];
