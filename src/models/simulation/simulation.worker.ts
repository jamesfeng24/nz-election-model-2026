import { handleRequest } from './worker';
import { syntheticStages } from './syntheticStages';
import type { PipelineRunRequest } from './pipeline';

// Thin Web Worker entry. Synthetic stages only until real components replace them; never bundled
// into the production site (see the synthetic-leak guard).
const scope = globalThis as unknown as { onmessage: ((e: { data: PipelineRunRequest }) => void) | null; postMessage(m: unknown): void };
scope.onmessage = e => handleRequest(e.data, syntheticStages, m => scope.postMessage(m), {
  asOf: new Date().toISOString(), limitations: ['Synthetic fixture run: not a forecast'],
});
