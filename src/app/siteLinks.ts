/**
 * Shown on the About page. A link with no `url` is hidden until one is added; `shown` is the text printed as the link
 * (an email address goes in `url` as `mailto:name@example.org`).
 */
export const SITE_LINKS: { label: string; shown: string; note: string; url: string | null }[] = [
  {
    label: 'GitHub',
    shown: 'github.com/jamesfeng24',
    note: 'Code and project updates',
    url: 'https://github.com/jamesfeng24',
  },
  { label: 'X', shown: '@jamesfeng24', note: 'News and updates', url: 'https://x.com/jamesfeng24' },
  {
    label: 'Email',
    shown: 'james.jiayi.feng@gmail.com',
    note: 'Questions about the forecast',
    url: 'mailto:james.jiayi.feng@gmail.com',
  },
  { label: 'Ko-fi', shown: '', note: 'Buy me a coffee if you find this useful', url: null },
];
