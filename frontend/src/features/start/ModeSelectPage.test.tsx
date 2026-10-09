import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../test/render';
import { ModeSelectPage } from './ModeSelectPage';

describe('ModeSelectPage', () => {
  it('개인 / 맞벌이 부부 입력 방식을 선택할 수 있다', async () => {
    const user = userEvent.setup();
    renderWithProviders(<></>, {
      routes: [
        { path: '/', element: <ModeSelectPage /> },
        { path: '/individual', element: <p>개인 화면</p> },
        { path: '/couple', element: <p>맞벌이 화면</p> },
      ],
    });
    expect(screen.getByRole('link', { name: /개인/ })).toHaveAttribute('href', '/individual');
    await user.click(screen.getByRole('link', { name: /맞벌이 부부/ }));
    expect(screen.getByText('맞벌이 화면')).toBeInTheDocument();
  });
});
