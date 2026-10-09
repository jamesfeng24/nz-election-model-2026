import { useEffect, useState } from 'react';
import { pages, type PageId } from './pages';
import { fetchText, loadArchiveIndex, loadLatestSnapshot, type IndexResult, type LoadResult } from '../data/loader';
import { ArchiveView } from './ArchiveView';
import { ElectoratesView } from './ElectoratesView';
import { ForecastView, SnapshotBanner } from './ForecastViews';
import { MethodologyView } from './MethodologyView';

/** Default sources read the published archive next to the page (`../forecasts/`). Development also allows the in-memory synthetic dry run. */
const options = () => ({ fetchText: fetchText(), baseUrl: new URL('../forecasts/', document.baseURI).href, allowSynthetic: import.meta.env.DEV });

export async function defaultSource(): Promise<LoadResult> {
  const published = await loadLatestSnapshot(options());
  if (import.meta.env.DEV && published.status !== 'loaded') {
    const { runSyntheticDryRun } = await import('../dev/syntheticSnapshot');
    return { status: 'loaded', snapshot: await runSyntheticDryRun() };
  }
  return published;
}
export const defaultIndexSource = (): Promise<IndexResult> => loadArchiveIndex(options());

type Loaded = LoadResult | { status: 'loading' };
const href = (path: string) => `../${path}/`;

export function App({ page, source = defaultSource, indexSource = defaultIndexSource }:
  { page: PageId; source?: () => Promise<LoadResult>; indexSource?: () => Promise<IndexResult> }) {
  const [result, setResult] = useState<Loaded>({ status: 'loading' });
  const [index, setIndex] = useState<IndexResult | { status: 'loading' }>({ status: 'loading' });
  useEffect(() => {
    let live = true;
    if (page === 'forecast' || page === 'electorates') source().then(r => { if (live) setResult(r); }, () => { if (live) setResult({ status: 'unavailable', reason: 'Could not load the forecast' }); });
    if (page === 'archive') indexSource().then(r => { if (live) setIndex(r); }, () => { if (live) setIndex({ status: 'unavailable', reason: 'Could not load the archive' }); });
    return () => { live = false; };
  }, [page, source, indexSource]);
  const current = pages.find(p => p.path === page)!;
  useEffect(() => { document.title = `${current.label} | NZ Election Model 2026`; }, [current]);
  return <>
    <a className="skip" href="#main">Skip to content</a>
    <header><a className="brand" href={href('forecast')}>NZ <span>Election Model</span><b>2026</b></a><span className="project-tag">INDEPENDENT RESEARCH PROJECT</span></header>
    <nav aria-label="Main navigation">{pages.map(p => <a key={p.path} href={href(p.path)} aria-current={p.path === page ? 'page' : undefined} className={p.path === page ? 'active' : undefined}>{p.label}</a>)}</nav>
    <main id="main">
      {(page === 'forecast' || page === 'electorates') && <>
        {result.status === 'loaded' && <SnapshotBanner snapshot={result.snapshot} />}
        <h1>{current.title}</h1>
        {result.status === 'loaded' ? (page === 'forecast' ? <ForecastView snapshot={result.snapshot} /> : <ElectoratesView snapshot={result.snapshot} />) : result.status === 'loading'
          ? <p role="status">Loading the latest forecast…</p>
          : <section className="status-panel"><h2>No forecast published yet</h2><p>The first forecast will appear here after the next weekly poll refresh. <a href={href('methodology')}>How it works</a>.</p></section>}
      </>}
      {page === 'methodology' && <><h1>{current.title}</h1><MethodologyView /></>}
      {page === 'archive' && <><h1>{current.title}</h1><ArchiveView result={index} /></>}
    </main>
    <footer><span>An independent research project, not an official election service.</span><a href="https://creativecommons.org/licenses/by/4.0/">Free to share with credit (CC BY 4.0)</a></footer>
  </>;
}
