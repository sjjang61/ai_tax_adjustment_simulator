import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { resetDb } from './handlers';
import { server } from './server';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
  resetDb();
});
afterAll(() => server.close());
