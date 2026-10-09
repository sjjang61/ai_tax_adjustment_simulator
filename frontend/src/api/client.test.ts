import { http, HttpResponse } from 'msw';
import { BASE } from '../test/handlers';
import { server } from '../test/server';
import { ApiError, api } from './client';

describe('api client', () => {
  it('통일 에러 응답을 ApiError로 변환한다', async () => {
    server.use(
      http.get(`${BASE}/simulations/1`, () =>
        HttpResponse.json(
          { code: 'not_found', message: '없음', details: { id: 1 } },
          { status: 404 },
        ),
      ),
    );
    const err = await api.getSimulation(1).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({
      status: 404,
      code: 'not_found',
      message: '없음',
      details: { id: 1 },
    });
  });

  it('형식이 다른 에러 응답도 처리한다', async () => {
    server.use(http.get(`${BASE}/rules`, () => new HttpResponse('oops', { status: 502 })));
    const err = await api.getRuleYears().catch((e: unknown) => e);
    expect(err).toMatchObject({ status: 502, code: 'http_error' });
  });

  it('쿼리 파라미터를 붙인다', async () => {
    let url = '';
    server.use(
      http.get(`${BASE}/simulations`, ({ request }) => {
        url = request.url;
        return HttpResponse.json([]);
      }),
    );
    await api.listSimulations(2025);
    expect(new URL(url).searchParams.get('tax_year')).toBe('2025');
    await api.listSimulations();
    expect(new URL(url).search).toBe('');
  });

  it('204 응답은 undefined', async () => {
    await expect(api.deleteSimulation(5)).resolves.toBeUndefined();
  });
});
