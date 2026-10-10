import { useEffect, useState } from 'react';
import {
  fetchText,
  loadArchiveIndex,
  loadLatestSnapshot,
  loadReleaseHistory,
  type IndexResult,
  type LoadResult,
  type ReleasePoint,
} from '../data/loader';
import { AboutView } from './AboutView';
import { ArchiveView } from './ArchiveView';
import { ElectoratesView } from './ElectoratesView';
import { ForecastView, SnapshotBanner } from './ForecastViews';
import { longDate } from './format';
import { MethodologyView } from './MethodologyView';
import { pages, type PageId } from './pages';
import { PollsView } from './PollsView';
import { MIN_RELEASES, TrendChart } from './TrendChart';

/** The published archive sits next to the pages. Development builds also allow the in-memory synthetic dry run. */
const loaderOptions = () => ({
  fetchText: fetchText(),
  baseUrl: new URL('../forecasts/', document.baseURI).href,
  allowSynthetic: import.meta.env.DEV,
});

export async function defaultSource(): Promise<LoadResult> {
  const published = await loadLatestSnapshot(loaderOptions());
  if (import.meta.env.DEV && published.status !== 'loaded') {
    const { runSyntheticDryRun } = await import('../dev/syntheticSnapshot');
    return { status: 'loaded', snapshot: await runSyntheticDryRun() };
  }
  return published;
}
export const defaultHistorySource = (): Promise<ReleasePoint[]> => loadReleaseHistory(loaderOptions());
export const defaultIndexSource = (): Promise<IndexResult> => loadArchiveIndex(loaderOptions());

type Loading = { status: 'loading' };
const pageHref = (path: string) => `../${path}/`;
/** A frozen copy sits at archive/<date>/<page>/, three levels below the live site's root. */
const LIVE_SITE = '../../../';

function Unavailable({ result }: { result: Extract<LoadResult, { status: 'unavailable' }> }) {
  if (result.cause === 'failed') {
    return (
      <section className="status-panel">
        <h2>The forecast could not be loaded</h2>
        <p>
          A forecast has been published, but this page could not read it. Try again shortly.{' '}
          <a href={pageHref('methodology')}>How it works</a>.
        </p>
      </section>
    );
  }
  return (
    <section className="status-panel">
      <h2>No forecast published yet</h2>
      <p>
        The first forecast will appear here after the next weekly poll refresh.{' '}
        <a href={pageHref('methodology')}>How it works</a>.
      </p>
    </section>
  );
}

function SnapshotPage({
  page,
  result,
  history,
}: {
  page: 'forecast' | 'electorates' | 'polls';
  result: LoadResult | Loading;
  history: ReleasePoint[];
}) {
  if (result.status === 'loading') return <p role="status">Loading the latest forecast…</p>;
  if (result.status === 'unavailable') return <Unavailable result={result} />;
  const { snapshot } = result;
  if (page === 'polls') return <PollsView snapshot={snapshot} />;
  if (page === 'electorates') return <ElectoratesView snapshot={snapshot} />;
  return (
    <ForecastView
      snapshot={snapshot}
      trend={history.length >= MIN_RELEASES ? <TrendChart history={history} /> : null}
    />
  );
}

export function App({
  page,
  source = defaultSource,
  indexSource = defaultIndexSource,
  historySource = defaultHistorySource,
  archivedOn = __ARCHIVE_DATE__ || undefined,
}: {
  page: PageId;
  /** Set in the frozen copy served from archive/<date>/: the forecast's date, shown in a banner linking to the live site. */
  archivedOn?: string;
  source?: () => Promise<LoadResult>;
  indexSource?: () => Promise<IndexResult>;
  historySource?: () => Promise<ReleasePoint[]>;
}) {
  const [result, setResult] = useState<LoadResult | Loading>({ status: 'loading' });
  const [history, setHistory] = useState<ReleasePoint[]>([]);
  const [index, setIndex] = useState<IndexResult | Loading>({ status: 'loading' });
  const current = pages.find((p) => p.path === page)!;

  useEffect(() => {
    let live = true;
    if (page === 'forecast' || page === 'electorates' || page === 'polls' || page === 'methodology') {
      source().then(
        (r) => live && setResult(r),
        () => live && setResult({ status: 'unavailable', reason: 'Could not load the forecast', cause: 'failed' }),
      );
    }
    if (page === 'forecast')
      historySource().then(
        (h) => live && setHistory(h),
        () => undefined,
      );
    if (page === 'archive') {
      indexSource().then(
        (r) => live && setIndex(r),
        () => live && setIndex({ status: 'unavailable', reason: 'Could not load the archive' }),
      );
    }
    return () => {
      live = false;
    };
  }, [page, source, indexSource, historySource]);

  useEffect(() => {
    document.title = `${current.label} | NZ Election Forecast`;
  }, [current]);

  const loaded = result.status === 'loaded' ? result.snapshot : undefined;
  const showsSnapshot = page === 'forecast' || page === 'electorates' || page === 'polls';
  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header>
        <a className="brand" href={pageHref('forecast')}>
          NZ <span>Election Forecast</span>
        </a>
      </header>
      <nav aria-label="Main navigation">
        {pages.map((p) => (
          <a
            key={p.path}
            href={pageHref(p.path)}
            aria-current={p.path === page ? 'page' : undefined}
            className={p.path === page ? 'active' : undefined}
          >
            {p.label}
          </a>
        ))}
      </nav>
      {archivedOn && (
        <p className="archive-banner" role="note">
          You&rsquo;re viewing the forecast from {longDate(archivedOn)}. <a href={LIVE_SITE}>See the latest</a>
        </p>
      )}
      <main id="main">
        {showsSnapshot && loaded && <SnapshotBanner snapshot={loaded} />}
        <h1>{current.title}</h1>
        {showsSnapshot && <SnapshotPage page={page} result={result} history={history} />}
        {page === 'methodology' && (
          <MethodologyView adjustments={loaded?.adjustments} incumbency={loaded?.incumbency} />
        )}
        {page === 'archive' && <ArchiveView result={index} archived={!!archivedOn} />}
        {page === 'about' && <AboutView />}
      </main>
      <footer>
        <a href="https://creativecommons.org/licenses/by/4.0/">Licensed under CC BY 4.0</a>
      </footer>
    </>
  );
}
