export interface MetadataSummary {
  columns: string[];
  matched: number;
  errors: string[];
}

// Quote-aware parse of the whole file, like Python's csv module on the server:
// a quoted field may hold the delimiter, doubled quotes and line breaks.
function parseTable(text: string, delimiter: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === delimiter) { row.push(cell); cell = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = '';
    } else cell += ch;
  }
  row.push(cell);
  rows.push(row);
  return rows.map((r) => r.map((c) => c.trim())).filter((r) => r.some(Boolean));
}

export function summarizeMetadata(filename: string, text: string, sampleNames: string[]): MetadataSummary {
  const lower = filename.toLowerCase().replace(/\.gz$/, '');
  if (!lower.endsWith('.tsv') && !lower.endsWith('.csv')) {
    return { columns: [], matched: 0, errors: ['Metadata must be a .tsv or .csv file.'] };
  }
  const rows = parseTable(text.replace(/^﻿/, ''), lower.endsWith('.tsv') ? '\t' : ',');
  if (rows.length === 0) return { columns: [], matched: 0, errors: ['Metadata file is empty.'] };
  const columns = rows[0].slice(1);
  const errors: string[] = [];
  if (columns.length === 0) errors.push('Metadata needs a sample-name column and at least one more column.');
  if (columns.includes('placed_sample')) errors.push("'placed_sample' is a reserved column name.");
  if (columns.some((c) => /[,\t\r\n]/.test(c))) errors.push('Metadata column names cannot contain commas, tabs or line breaks.');
  const names = new Set(sampleNames);
  const seen = new Set<string>();
  let matched = 0;
  rows.slice(1).forEach((row, i) => {
    const name = row[0];
    if (seen.has(name)) errors.push(`Row ${i + 2}: duplicate sample '${name}'.`);
    else if (!names.has(name)) errors.push(`Row ${i + 2}: sample '${name}' is not in the FASTA file.`);
    else matched++;
    seen.add(name);
  });
  return { columns, matched, errors };
}
