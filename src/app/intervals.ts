import { PRIMARY_INTERVAL_LEVEL, type IntervalSet } from '../types/domain';

export const intervalAt = (set: IntervalSet, level: number) => set.find((v) => v.level === level)!;

/** The 80% range every page shows. */
export const mainRange = (set: IntervalSet) => intervalAt(set, PRIMARY_INTERVAL_LEVEL);
