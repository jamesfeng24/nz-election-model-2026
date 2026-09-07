import { describe, expect, it } from 'vitest';
import { SourceRecordSchema, SourceRegistrySchema } from './contracts';
import registry from '../../data/sources.json';
// Synthetic metadata only. This is not an election observation.
const fixture = { schemaVersion:1, id:'test-source', organisation:'Synthetic test organisation', url:'https://example.org/fixture', dateOrElection:'test only', resource:'Synthetic metadata fixture', retrievedAt:'2026-01-01T00:00:00Z', rawPath:'data/raw/fixture.txt', processingScript:null, limitations:['Synthetic; never use for modelling'], sha256:'a'.repeat(64), licence:'Test fixture' };
describe('source contracts', () => {
 it('validates the real source registry', () => { expect(SourceRegistrySchema.parse(registry).sources).toHaveLength(registry.sources.length); });
 it('accepts labelled synthetic metadata', () => { expect(SourceRecordSchema.safeParse(fixture).success).toBe(true); });
 it.each([{url:'invalid'}, {retrievedAt:'yesterday'}, {sha256:'bad'}, {rawPath:'data/raw/../../secret'}, {organisation:''}, {limitations:[]}])('rejects invalid metadata %j', patch => {expect(SourceRecordSchema.safeParse({...fixture,...patch}).success).toBe(false);});
 it('requires all provenance fields', () => {expect(SourceRecordSchema.safeParse({schemaVersion:1}).success).toBe(false);});
 it('rejects duplicate ids', () => {expect(SourceRegistrySchema.safeParse({schemaVersion:1,sources:[fixture,fixture]}).success).toBe(false);});
});
