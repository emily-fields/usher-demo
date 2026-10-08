const FASTA_EXTENSIONS = ['.fa', '.fasta', '.fna'];
const SEQUENCE_RE = /^[ACGTURYSWKMBDHVN-]+$/i;
const NAME_RE = /^[A-Za-z0-9._\-/|]+$/;
const ACCESSION_ALIASES: Record<string, string> = { 'OR957580.1': 'NC_045512.2' };
export const HEADER_HINT = "Each header must look like '>ACCESSION sample_name'";

export interface FastaSummary {
  accession: string | null;
  records: { name: string; length: number }[];
  errors: string[];
}

export function isFastaFilename(name: string): boolean {
  const lower = name.toLowerCase().replace(/\.gz$/, '');
  return FASTA_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export function summarizeFasta(filename: string, text: string): FastaSummary {
  if (!isFastaFilename(filename)) {
    return { accession: null, records: [], errors: ['Only FASTA files are accepted (.fa, .fasta, .fna, optionally .gz).'] };
  }
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (!lines[0]?.startsWith('>')) {
    return { accession: null, records: [], errors: ["This does not look like FASTA: the first line must start with '>'."] };
  }
  const blocks: { header: string; seq: string }[] = [];
  for (const line of lines) {
    if (line.startsWith('>')) blocks.push({ header: line.slice(1).trim(), seq: '' });
    else blocks[blocks.length - 1].seq += line;
  }
  const errors: string[] = [];
  const accessions = new Set<string>();
  const seen = new Set<string>();
  const records = blocks.map(({ header, seq }, i) => {
    const [first, second] = header.split(/\s+/);
    if (first) accessions.add(ACCESSION_ALIASES[first] ?? first);
    const name = second ?? `sample_${i + 1}`;
    const label = `Record ${i + 1} (${name})`;
    if (!first) errors.push(`Record ${i + 1}: header is empty. ${HEADER_HINT}.`);
    if (!NAME_RE.test(name)) errors.push(`${label}: sample names may only contain letters, digits and . _ - / |`);
    if (seen.has(name)) errors.push(`${label}: duplicate sample name.`);
    seen.add(name);
    if (!seq) errors.push(`${label}: sequence is empty.`);
    else if (!SEQUENCE_RE.test(seq)) errors.push(`${label}: sequence contains characters that are not IUPAC nucleotide codes.`);
    return { name, length: seq.length };
  });
  if (accessions.size > 1) {
    errors.push(`All records must start with the same reference accession; found ${[...accessions].join(', ')}. ${HEADER_HINT}.`);
  }
  return { accession: accessions.size === 1 ? [...accessions][0] : null, records, errors };
}
