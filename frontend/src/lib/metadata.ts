export interface MetadataSummary {
  columns: string[];
  matched: number;
  errors: string[];
}

function splitRow(line: string, delimiter: string): string[] {
  if (delimiter === '\t') return line.split('\t');
  const cells: string[] = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quoted && ch === '"' && line[i + 1] === '"') { cell += '"'; i++; }
    else if (ch === '"') quoted = !quoted;
    else if (ch === delimiter && !quoted) { cells.push(cell); cell = ''; }
    else cell += ch;
  }
  cells.push(cell);
  return cells;
}

export function summarizeMetadata(filename: string, text: string, sampleNames: string[]): MetadataSummary {
  const lower = filename.toLowerCase().replace(/\.gz$/, '');
  if (!lower.endsWith('.tsv') && !lower.endsWith('.csv')) {
    return { columns: [], matched: 0, errors: ['Metadata must be a .tsv or .csv file.'] };
  }
  const delimiter = lower.endsWith('.tsv') ? '\t' : ',';
  const rows = text.replace(/^﻿/, '').split(/\r?\n/).filter((l) => l.trim()).map((l) => splitRow(l, delimiter).map((c) => c.trim()));
  if (rows.length === 0) return { columns: [], matched: 0, errors: ['Metadata file is empty.'] };
  const columns = rows[0].slice(1);
  const errors: string[] = [];
  if (columns.length === 0) errors.push('Metadata needs a sample-name column and at least one more column.');
  if (columns.includes('placed_sample')) errors.push("'placed_sample' is a reserved column name.");
  const names = new Set(sampleNames);
  const seen = new Set<string>();
  let matched = 0;
  rows.slice(1).forEach((row, i) => {
    const name = row[0];
    if (seen.has(name)) errors.push(`Line ${i + 2}: duplicate sample '${name}'.`);
    else if (!names.has(name)) errors.push(`Line ${i + 2}: sample '${name}' is not in the FASTA file.`);
    else matched++;
    seen.add(name);
  });
  return { columns, matched, errors };
}
