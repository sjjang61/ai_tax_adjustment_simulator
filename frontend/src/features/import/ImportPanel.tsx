import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import type { SimulationExport } from '../../api/types';
import { ApiErrorMessage } from '../../components/ApiErrorMessage';
import { readJsonFile } from './download';

type ImportPanelProps = { supportedYears: readonly number[]; defaultYear: number };

/** JSON 파일 가져오기. 대상 연도를 고르면 서버에서 연도 이월 변환까지 수행한다. */
export function ImportPanel({ supportedYears, defaultYear }: ImportPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [targetYear, setTargetYear] = useState<string>('');
  const [parseError, setParseError] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const importMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('파일을 선택하세요.');
      let doc: unknown;
      try {
        doc = await readJsonFile(file);
      } catch {
        throw new Error('JSON 파일을 읽을 수 없습니다.');
      }
      return api.importSimulation(
        doc as SimulationExport,
        targetYear ? Number(targetYear) : undefined,
      );
    },
    onSuccess: async (res) => {
      await queryClient.invalidateQueries({ queryKey: ['simulations'] });
      navigate(`/simulations/${res.simulation.id}`, {
        state: { carryOverWarnings: res.warnings },
      });
    },
  });

  return (
    <section className="panel" aria-label="JSON 파일 가져오기">
      <h2>JSON 파일 가져오기</h2>
      <p className="section__note">
        내보낸 시뮬레이션 파일(.json)을 불러옵니다. 대상 연도를 고르면 작년 데이터를 올해 초안으로
        변환합니다.
      </p>
      <form
        className="import-form"
        onSubmit={(e) => {
          e.preventDefault();
          setParseError(null);
          if (!file) {
            setParseError('파일을 선택하세요.');
            return;
          }
          importMutation.mutate();
        }}
      >
        <div className="field">
          <span className="field__label">파일</span>
          <label className="file-picker">
            <input
              type="file"
              className="visually-hidden"
              aria-label="파일"
              accept="application/json,.json"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <span className="btn btn--ghost btn--small" aria-hidden="true">
              파일 선택
            </span>
            <span className="file-picker__name">{file?.name ?? '선택된 파일 없음 (.json)'}</span>
          </label>
        </div>
        <label>
          변환할 귀속연도
          <select value={targetYear} onChange={(e) => setTargetYear(e.target.value)}>
            <option value="">변환하지 않음 (파일의 연도 유지)</option>
            {supportedYears.map((y) => (
              <option key={y} value={y}>
                {y}년 귀속{y === defaultYear ? ' (기본)' : ''}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="btn btn--primary" disabled={importMutation.isPending}>
          가져오기
        </button>
      </form>
      {parseError ? (
        <p className="field__error" role="alert">
          {parseError}
        </p>
      ) : null}
      <ApiErrorMessage error={importMutation.error} />
    </section>
  );
}
