import { SITE_LINKS } from './siteLinks';

/** Who runs the site and where to find them. Only links that have an address are shown. */
export function AboutView() {
  const links = SITE_LINKS.filter(l => l.url);
  return <article className="prose">
    <p>NZ Election Forecast is an independent project. It is not run by a news outlet, a party or the Electoral Commission. <a href="../methodology/">How the forecast works</a>.</p>
    {links.length > 0 && <>
      <h2>Find me, or get in touch</h2>
      <ul className="linklist">{links.map(l => <li key={l.label}><a href={l.url!} rel="noopener noreferrer">{l.label}</a> <span>{l.note}</span></li>)}</ul>
    </>}
  </article>;
}
