import type { SimulationWorkerResponse } from '../../types/domain';
import { runPipeline, type PipelineRunRequest, type PipelineStages } from './pipeline';

/**
 * Message handler kept free of `self`/DOM so it is testable and reusable. The thin worker entry
 * (simulation.worker.ts) wires it to postMessage. The UI owns cancellation by terminating the worker
 * and discarding responses whose requestId is stale (see createRunTracker).
 */
export function handleRequest(
  request: PipelineRunRequest, stages: PipelineStages, post: (message: SimulationWorkerResponse) => void,
  options: { asOf: string; limitations: string[]; progressEvery?: number },
): void {
  try {
    const every = options.progressEvery ?? 100;
    const output = runPipeline(request.config, request.inputs, stages, {
      runId: request.requestId, asOf: options.asOf, limitations: options.limitations,
      onProgress: n => { if (n % every === 0 && n < request.config.draws) post({ type: 'progress', requestId: request.requestId, completedDraws: n }); },
    });
    post({ type: 'result', requestId: request.requestId, result: output.result });
  } catch (error) {
    post({ type: 'error', requestId: request.requestId, message: error instanceof Error ? error.message : String(error) });
  }
}

/** Accepts only responses for the latest request. */
export function createRunTracker() {
  let current: string | null = null;
  return {
    start(requestId: string) { current = requestId; },
    accepts(message: SimulationWorkerResponse) { return message.requestId === current; },
  };
}
