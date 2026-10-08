import { describe, expect, it } from 'vitest';
import { summarizeMetadata } from './metadata';

describe('summarizeMetadata', () => {
  it('keeps quoted CSV values with commas and line breaks in one row', () => {
    const s = summarizeMetadata('m.csv', 'sample,note\ns1,"two\nlines, one value"\n', ['s1']);
    expect(s).toEqual({ columns: ['note'], matched: 1, errors: [] });
  });

  it('strips quotes around TSV sample names', () => {
    expect(summarizeMetadata('m.tsv', 'sample\tdate\n"s1"\t2024\n', ['s1']).matched).toBe(1);
  });

  it('rejects column names that would break the tree view', () => {
    const s = summarizeMetadata('m.csv', 'sample,"Location, city"\ns1,LA\n', ['s1']);
    expect(s.errors.some((e) => e.includes('column names cannot contain'))).toBe(true);
  });
});
