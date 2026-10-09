import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { MoneyInput } from './MoneyInput';

function Harness({ initial = 0, onValue }: { initial?: number; onValue?: (v: number) => void }) {
  const [value, setValue] = useState(initial);
  return (
    <>
      <label htmlFor="m">금액</label>
      <MoneyInput
        id="m"
        value={value}
        onChange={(v) => {
          setValue(v);
          onValue?.(v);
        }}
      />
      <output data-testid="value">{value}</output>
    </>
  );
}

describe('MoneyInput', () => {
  it('저장 값은 원 단위 정수, 표시는 천 단위 콤마', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const input = screen.getByLabelText('금액');
    await user.type(input, '1234567');
    expect(screen.getByTestId('value')).toHaveTextContent('1234567');
    await user.tab();
    expect(input).toHaveValue('1,234,567');
    expect(screen.getByText('123만 4,567원')).toBeInTheDocument();
  });

  it('만·억 단위 입력을 원으로 변환한다', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const input = screen.getByLabelText('금액');
    await user.type(input, '3000만');
    expect(screen.getByTestId('value')).toHaveTextContent('30000000');
    await user.clear(input);
    await user.type(input, '1.5억');
    expect(screen.getByTestId('value')).toHaveTextContent('150000000');
    await user.tab();
    expect(input).toHaveValue('150,000,000');
  });

  it('형식 오류는 메시지를 보여주고 값은 유지한다', async () => {
    const user = userEvent.setup();
    render(<Harness initial={5000} />);
    const input = screen.getByLabelText('금액');
    expect(input).toHaveValue('5,000');
    await user.clear(input);
    await user.type(input, 'abc');
    expect(screen.getByRole('alert')).toHaveTextContent('금액 형식이 올바르지 않습니다');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    // clear 시 빈 문자열 → 0으로 반영된 뒤, 해석 불가 입력은 값 변경 없음
    expect(screen.getByTestId('value')).toHaveTextContent('0');
  });
});
