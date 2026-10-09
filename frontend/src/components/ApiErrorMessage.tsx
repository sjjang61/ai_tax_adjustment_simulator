import { ApiError } from '../api/client';

export function ApiErrorMessage({ error }: { error: unknown }) {
  if (!error) return null;
  const message =
    error instanceof ApiError
      ? `${error.message} (${error.code})`
      : error instanceof Error
        ? error.message
        : '알 수 없는 오류가 발생했습니다.';
  return (
    <div className="alert alert--error" role="alert">
      {message}
    </div>
  );
}
