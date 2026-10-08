import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { Organism } from '@/lib/api';
import type { FastaSummary } from '@/lib/fasta';
import type { MetadataSummary } from '@/lib/metadata';

interface Props {
  fasta: FastaSummary;
  organism: Organism | undefined;
  metadata: MetadataSummary | null;
}

export function UploadPreview({ fasta, organism, metadata }: Props) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span>{fasta.records.length} sequence{fasta.records.length === 1 ? '' : 's'}</span>
        {fasta.accession && <Badge variant="outline" className="font-mono">{fasta.accession}</Badge>}
        {organism && <Badge>{organism.organism} · {organism.leaf_count.toLocaleString()} samples</Badge>}
        {metadata && metadata.errors.length === 0 && (
          <Badge variant="secondary">
            Metadata: {metadata.columns.join(', ')} ({metadata.matched}/{fasta.records.length} matched)
          </Badge>
        )}
      </div>
      <div className="max-h-64 overflow-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Sample</TableHead>
              <TableHead className="text-right">Length</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {fasta.records.map((r) => (
              <TableRow key={r.name}>
                <TableCell className="font-mono">{r.name}</TableCell>
                <TableCell className="text-right">{r.length.toLocaleString()} bp</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
