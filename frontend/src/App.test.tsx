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

function activeIn(name: string) {
  return screen.getByRole('navigation', { name }).querySelector('a.active');
}

describe('App 메뉴', () => {
  it('상단에 연말정산·종합소득세 두 메뉴를 구분해 보여준다', () => {
    renderAt('/');
    const nav = screen.getByRole('navigation', { name: '주요 메뉴' });
    expect(nav).toHaveTextContent('연말정산 시뮬레이터');
    expect(nav).toHaveTextContent('종합소득세 시뮬레이터');
  });

  it.each(['/', '/individual', '/couple', '/saved'])('%s 는 연말정산 메뉴가 활성', (path) => {
    renderAt(path);
    expect(activeIn('주요 메뉴')).toHaveTextContent('연말정산 시뮬레이터');
    expect(screen.getByRole('navigation', { name: '연말정산 메뉴' })).toBeInTheDocument();
  });

  it.each([
    ['/', '새 계산'],
    ['/couple', '새 계산'],
    ['/saved', '저장·불러오기'],
  ])('%s 연말정산 보조 메뉴 활성: %s', (path, label) => {
    renderAt(path);
    expect(activeIn('연말정산 메뉴')).toHaveTextContent(label);
  });

  it.each([
    ['/global-income', '저장 목록'],
    ['/global-income/new', '새 계산'],
    ['/global-income/businesses', '사업자 관리'],
    ['/global-income/businesses/3/partnership', '사업자 관리'],
  ])('%s 는 종합소득세 메뉴가 활성 (보조: %s)', (path, label) => {
    renderAt(path);
    expect(activeIn('주요 메뉴')).toHaveTextContent('종합소득세 시뮬레이터');
    expect(activeIn('종합소득세 메뉴')).toHaveTextContent(label);
  });

  it('시작 화면에서 저장한 시뮬레이션 불러오기로 이동할 수 있다', () => {
    renderAt('/');
    expect(screen.getByRole('link', { name: /저장한 시뮬레이션 불러오기/ })).toHaveAttribute(
      'href',
      '/saved',
    );
  });
});
