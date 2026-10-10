import { describe, expect, it } from 'vitest';
import { HttpError, loadArchiveIndex, loadLatestSnapshot } from './loader';

const entry = (snapshotId: string, provenanceKind: 'model' | 'synthetic-fixture') => ({
  snapshotId,
  createdAt: '2026-10-09T00:00:00+13:00',
  dataCutoff: '2026-10-09T00:00:00+13:00',
  provenanceKind,
  path: `${snapshotId}/snapshot.json`,
  sha256: 'a'.repeat(64),
  supersedes: null,
  status: 'published',
  withdrawnReason: null,
});
const serve = (snapshots: unknown[]) => async () => JSON.stringify({ schemaVersion: 1, snapshots });

describe('archive index loader', () => {
  it('drops synthetic entries unless development allows them', async () => {
    const fetchText = serve([entry('synthetic-a', 'synthetic-fixture'), entry('b', 'model')]);
    const prod = await loadArchiveIndex({ fetchText, baseUrl: '../forecasts/', allowSynthetic: false });
    expect(prod.status === 'loaded' && prod.index.snapshots.map((e) => e.snapshotId)).toEqual(['b']);
    const dev = await loadArchiveIndex({ fetchText, baseUrl: '../forecasts/', allowSynthetic: true });
    expect(dev.status === 'loaded' && dev.index.snapshots).toHaveLength(2);
  });
  it('reports unavailable for a missing or invalid index', async () => {
    expect(
      (
        await loadArchiveIndex({
          fetchText: async () => {
            throw new Error('HTTP 404');
          },
          baseUrl: 'x',
          allowSynthetic: false,
        })
      ).status,
    ).toBe('unavailable');
    expect(
      (await loadArchiveIndex({ fetchText: async () => '{"schemaVersion":9}', baseUrl: 'x', allowSynthetic: false }))
        .status,
    ).toBe('unavailable');
  });
});

describe('latest snapshot loader', () => {
  const load = (fetchText: (url: string) => Promise<string>) =>
    loadLatestSnapshot({ fetchText, baseUrl: '../forecasts/', allowSynthetic: false });
  it('says nothing is published yet when the index is missing or lists no forecast', async () => {
    const missing = await load(async (url) => {
      throw new HttpError(url, 404);
    });
    expect(missing).toMatchObject({ status: 'unavailable', cause: 'none-published' });
    expect(await load(serve([]))).toMatchObject({ status: 'unavailable', cause: 'none-published' });
  });
  it('says the forecast failed to load when the archive is unreachable or does not verify', async () => {
    expect(
      await load(async (url) => {
        throw new HttpError(url, 500);
      }),
    ).toMatchObject({ status: 'unavailable', cause: 'failed' });
    expect(
      await load(async () => {
        throw new Error('network down');
      }),
    ).toMatchObject({ status: 'unavailable', cause: 'failed' });
    const wrongHash = async (url: string) => (url.endsWith('index.json') ? serve([entry('b', 'model')])() : '{}');
    expect(await load(wrongHash)).toMatchObject({ status: 'unavailable', cause: 'failed' });
  });
});
