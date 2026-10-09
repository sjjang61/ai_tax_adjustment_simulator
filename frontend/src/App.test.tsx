import { QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';
import { createTestQueryClient } from './test/render';

function renderAt(path: string) {
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('App 메뉴', () => {
  it.each(['/', '/individual', '/couple'])('%s 에서는 「새 시뮬레이션」이 활성', (path) => {
    renderAt(path);
    const nav = screen.getByRole('navigation', { name: '주요 메뉴' });
    expect(nav.querySelector('a.active')).toHaveTextContent('새 시뮬레이션');
  });

  it('/saved 에서는 「저장·불러오기」가 활성', () => {
    renderAt('/saved');
    const nav = screen.getByRole('navigation', { name: '주요 메뉴' });
    expect(nav.querySelector('a.active')).toHaveTextContent('저장·불러오기');
  });

  it('시작 화면에서 저장한 시뮬레이션 불러오기로 이동할 수 있다', () => {
    renderAt('/');
    expect(screen.getByRole('link', { name: /저장한 시뮬레이션 불러오기/ })).toHaveAttribute(
      'href',
      '/saved',
    );
  });
});
