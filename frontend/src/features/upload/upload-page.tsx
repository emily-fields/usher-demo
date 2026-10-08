import { AlertCircle, ChevronDown, LoaderCircle, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { ApiError, api, useCreateJob, useOrganisms } from '@/lib/api';
import { HEADER_HINT, summarizeFasta, type FastaSummary } from '@/lib/fasta';
import { readFileText } from '@/lib/files';
import { summarizeMetadata, type MetadataSummary } from '@/lib/metadata';
import { FileDropZone } from './file-drop-zone';
import { UploadPreview } from './upload-preview';

export default function UploadPage() {
  const navigate = useNavigate();
  const organisms = useOrganisms();
  const createJob = useCreateJob();
  const [fastaFile, setFastaFile] = useState<File | null>(null);
  const [metadataFile, setMetadataFile] = useState<File | null>(null);
  const [fasta, setFasta] = useState<FastaSummary | null>(null);
  const [metadata, setMetadata] = useState<MetadataSummary | null>(null);
  const [serverErrors, setServerErrors] = useState<string[]>([]);

  useEffect(() => {
    setServerErrors([]);
    if (!fastaFile) return setFasta(null);
    let cancelled = false;
    readFileText(fastaFile)
      .then((text) => !cancelled && setFasta(summarizeFasta(fastaFile.name, text)))
      .catch(() => !cancelled && setFasta({ accession: null, records: [], errors: ['Could not read this file.'] }));
    return () => { cancelled = true; };
  }, [fastaFile]);

  useEffect(() => {
    setServerErrors([]);
    if (!metadataFile) return setMetadata(null);
    let cancelled = false;
    const names = fasta?.records.map((r) => r.name) ?? [];
    readFileText(metadataFile)
      .then((text) => !cancelled && setMetadata(summarizeMetadata(metadataFile.name, text, names)))
      .catch(() => !cancelled && setMetadata({ columns: [], matched: 0, errors: ['Could not read this file.'] }));
    return () => { cancelled = true; };
  }, [metadataFile, fasta]);

  const available = organisms.data ?? [];
  const organism = available.find((o) => o.accession === fasta?.accession);
  const supported = available.map((o) => `${o.accession} (${o.organism})`).join(', ');
  const clientErrors = [
    ...(fasta?.errors ?? []),
    ...(fasta?.accession && organisms.data && !organism ? [`${fasta.accession} is not supported. Use one of: ${supported}.`] : []),
    ...(metadata?.errors ?? []),
  ];
  const errors = serverErrors.length ? serverErrors : clientErrors;
  const canSubmit = !!fastaFile && !!fasta && clientErrors.length === 0 && !createJob.isPending;

  async function loadExample(key: string) {
    try {
      const [f, m] = await Promise.all([api.getExampleFile(key, 'fasta'), api.getExampleFile(key, 'metadata')]);
      setFastaFile(f);
      setMetadataFile(m);
    } catch {
      toast.error('Could not load the example.');
    }
  }

  function submit() {
    if (!fastaFile) return;
    createJob.mutate(
      { fasta: fastaFile, metadata: metadataFile },
      {
        onSuccess: ({ id }) => navigate(`/jobs/${id}`),
        onError: (e) => setServerErrors(e instanceof ApiError ? e.errors : [String(e)]),
      },
    );
  }

  return (
    <Card className="mx-auto max-w-3xl">
      <CardHeader>
        <CardTitle>Place sequences on a phylogenetic tree</CardTitle>
        <CardDescription>
          Upload a FASTA file and UShER will place each sequence onto a pre-built tree. {HEADER_HINT}
          {supported && <> — supported: {supported}.</>}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <FileDropZone label="FASTA" hint=".fa, .fasta, .fna (optionally .gz)" accept=".fa,.fasta,.fna,.gz"
            file={fastaFile} onFile={setFastaFile} />
          <FileDropZone label="Metadata (optional)" hint=".tsv or .csv, first column = sample name" accept=".tsv,.csv"
            file={metadataFile} onFile={setMetadataFile} />
        </div>
        {fasta && fasta.records.length > 0 && <UploadPreview fasta={fasta} organism={organism} metadata={metadata} />}
        {errors.length > 0 && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertTitle>Please fix the following</AlertTitle>
            <AlertDescription>
              <ul className="list-disc pl-4">{errors.map((e) => <li key={e}>{e}</li>)}</ul>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
      <CardFooter className="flex justify-between gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" disabled={!available.some((o) => o.has_example)}>
              <Sparkles className="size-4" /> Try an example <ChevronDown className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {available.filter((o) => o.has_example).map((o) => (
              <DropdownMenuItem key={o.key} onSelect={() => loadExample(o.key)}>{o.organism}</DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <Button onClick={submit} disabled={!canSubmit}>
          {createJob.isPending && <LoaderCircle className="size-4 animate-spin" />}
          Place samples
        </Button>
      </CardFooter>
    </Card>
  );
}
