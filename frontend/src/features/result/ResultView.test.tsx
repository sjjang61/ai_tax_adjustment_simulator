import { render, screen, within } from '@testing-library/react';
import type { TaxResult } from '../../api/types';
import { fixtureResult } from '../../test/handlers';
import { ResultView } from './ResultView';

describe('ResultView', () => {
  it('환급 요약·단계별 계산·고지를 표시한다', () => {
    render(<ResultView result={fixtureResult} />);
    expect(screen.getByText('예상 환급액')).toBeInTheDocument();
    expect(screen.getByTestId('total-balance')).toHaveTextContent(
      `${Math.abs(fixtureResult.total_balance_due).toLocaleString('ko-KR')}원`,
    );
    expect(screen.getByRole('note')).toHaveTextContent(
      '정확한 금액은 국세청 홈택스 연말정산 간소화 서비스 및 회사 정산 결과를 확인하세요',
    );
    const flow = screen.getByRole('region', { name: '단계별 계산 내역' });
    expect(within(flow).getByText('= 과세표준')).toBeInTheDocument();
    expect(within(flow).getByText('= 결정세액')).toBeInTheDocument();
  });

  it('소득공제·세액공제 내역과 한도 적용 배지를 보여준다', () => {
    render(<ResultView result={fixtureResult} />);
    const income = screen.getByRole('region', { name: '소득공제' });
    expect(within(income).getByText('인적공제')).toBeInTheDocument();
    expect(within(income).getAllByText('1명/건').length).toBeGreaterThan(0);
    const credits = screen.getByRole('region', { name: '세액공제' });
    expect(within(credits).getByText('근로소득세액공제')).toBeInTheDocument();
    expect(within(credits).getAllByText('한도·요건 적용').length).toBeGreaterThan(0);
  });

  it('공제 방식 비교에서 적용 방식을 표시한다', () => {
    render(<ResultView result={fixtureResult} />);
    const table = screen.getByRole('region', { name: '공제 방식 비교' });
    expect(within(table).getByText('적용')).toBeInTheDocument();
  });

  it('추가 납부·경고·미검증 규칙을 표시한다', () => {
    const result: TaxResult = {
      ...fixtureResult,
      tax_year: 2026,
      rules_verified: false,
      total_balance_due: 120000,
      warnings: [{ code: 'x', message: '나이 요건 미충족', level: 'warning', field: null }],
    };
    render(<ResultView result={result} />);
    expect(screen.getByText('예상 추가 납부액')).toBeInTheDocument();
    expect(screen.getByText('나이 요건 미충족')).toBeInTheDocument();
    expect(screen.getByText(/2026년 귀속 세법 규칙은 아직/)).toBeInTheDocument();
  });
});
