import { describe, expect, it } from 'vitest';
import { isFastaFilename, summarizeFasta } from './fasta';

describe('summarizeFasta', () => {
  it('reads records, default names and the accession', () => {
    const s = summarizeFasta('a.fasta', '>NC_001803.1 s1\r\nacgt\r\n>NC_001803.1\nAC\n');
    expect(s.accession).toBe('NC_001803.1');
    expect(s.records).toEqual([{ name: 's1', length: 4 }, { name: 'sample_2', length: 2 }]);
    expect(s.errors).toEqual([]);
  });

  it('flags mixed accessions and bad characters', () => {
    const s = summarizeFasta('a.fa', '>NC_001803.1 a\nACXT\n>soar_id=2\nAC\n');
    expect(s.errors.some((e) => e.includes('not IUPAC'))).toBe(true);
    expect(s.errors.some((e) => e.includes('>ACCESSION sample_name'))).toBe(true);
  });

  it('only accepts FASTA extensions', () => {
    expect(isFastaFilename('x.fa.gz')).toBe(true);
    expect(isFastaFilename('x.vcf')).toBe(false);
  });
});
