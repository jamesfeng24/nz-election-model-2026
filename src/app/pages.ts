/** Each page is its own static HTML file at `<path>/index.html`, so links between them are relative. */
export const pages = [
  { path: 'forecast', label: 'Forecast', title: 'Forecast' },
  { path: 'electorates', label: 'Electorates', title: 'Electorates' },
  { path: 'polls', label: 'Polls', title: 'Polls' },
  { path: 'methodology', label: 'Methodology', title: 'Methodology' },
  { path: 'archive', label: 'Archive', title: 'Archive' },
  { path: 'about', label: 'About', title: 'About' },
] as const;

export type PageId = (typeof pages)[number]['path'];
