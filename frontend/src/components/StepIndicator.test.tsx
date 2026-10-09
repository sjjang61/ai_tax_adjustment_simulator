import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StepIndicator } from './StepIndicator';

const STEPS = ['기본 정보', '인적공제', '소득공제', '세액공제', '결과'] as const;

describe('StepIndicator', () => {
  it('진행 단계를 프로세스 형태로 표시한다 (완료·현재·예정)', () => {
    render(<StepIndicator steps={STEPS} current={2} onSelect={vi.fn()} />);
    const nav = screen.getByRole('navigation', { name: '입력 단계' });
    expect(within(nav).getByText('3 / 5 단계')).toBeInTheDocument();

    const done = within(nav).getByRole('button', { name: '1단계 기본 정보 (완료)' });
    expect(done).toHaveTextContent('✓');
    const current = within(nav).getByRole('button', { name: '3단계 소득공제 (현재 단계)' });
    expect(current).toHaveAttribute('aria-current', 'step');
    const upcoming = within(nav).getByRole('button', { name: '5단계 결과' });
    expect(upcoming).not.toHaveAttribute('aria-current');

    const items = within(nav).getAllByRole('listitem');
    expect(items.map((li) => li.dataset.state)).toEqual([
      'done',
      'done',
      'current',
      'todo',
      'todo',
    ]);
  });

  it('어느 단계든 클릭하면 바로 이동한다 (이후 단계 포함)', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<StepIndicator steps={STEPS} current={0} onSelect={onSelect} />);
    await user.click(screen.getByRole('button', { name: '4단계 세액공제' }));
    expect(onSelect).toHaveBeenLastCalledWith(3);
    await user.click(screen.getByRole('button', { name: '5단계 결과' }));
    expect(onSelect).toHaveBeenLastCalledWith(4);
  });

  it('현재 단계를 다시 누르면 아무 일도 하지 않는다', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<StepIndicator steps={STEPS} current={1} onSelect={onSelect} />);
    await user.click(screen.getByRole('button', { name: '2단계 인적공제 (현재 단계)' }));
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('onSelect가 없으면 이동 버튼을 비활성화한다', () => {
    render(<StepIndicator steps={STEPS} current={1} />);
    expect(screen.getByRole('button', { name: '4단계 세액공제' })).toBeDisabled();
  });
});
