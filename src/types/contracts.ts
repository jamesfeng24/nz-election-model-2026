import { z } from 'zod';
/** Infrastructure contracts only; no political observations or model assumptions. */
export const SourceRecordSchema = z.object({
 schemaVersion: z.literal(1), id: z.string().min(1), organisation: z.string().min(1),
 url: z.url(), dateOrElection: z.string().min(1), resource: z.string().min(1),
 retrievedAt: z.iso.datetime({ offset: true }), rawPath: z.string().regex(/^data\/raw\/(?!.*\.\.)(?!.*\\).+/),
 processingScript: z.string().regex(/^scripts\/(?!.*\.\.)(?!.*\\).+/).nullable(),
 limitations: z.array(z.string().min(1)).min(1), sha256: z.string().regex(/^[a-f0-9]{64}$/),
 licence: z.string().min(1),
}).strict();
export const SourceRegistrySchema = z.object({schemaVersion: z.literal(1), sources: z.array(SourceRecordSchema)}).strict().superRefine((registry, ctx) => {
 const ids = new Set<string>();
 registry.sources.forEach((source, index) => { if (ids.has(source.id)) ctx.addIssue({code:'custom', message:'Duplicate source id', path:['sources', index, 'id']}); ids.add(source.id); });
});
export type SourceRecord = z.infer<typeof SourceRecordSchema>;
export type SourceRegistry = z.infer<typeof SourceRegistrySchema>;
/** Missing results cannot be confused with numerical zero. */
export type Availability<T> = { status: 'unavailable'; reason: string } | { status: 'available'; value: T; sourceIds: string[] };
