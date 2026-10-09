/** Public pages. Each is its own static HTML file (`<path>/index.html`), so links are plain relative addresses. */
export const pages = [
  { path: 'forecast', label: 'Forecast', title: 'Forecast if the election were held today' },
  { path: 'methodology', label: 'Methodology', title: 'How the forecast works' },
  { path: 'archive', label: 'Archive', title: 'Every published forecast' },
] as const;
export type PageId = typeof pages[number]['path'];
