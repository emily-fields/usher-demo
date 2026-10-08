import { useMutation, useQuery } from '@tanstack/react-query';

export type JobStatus = 'queued' | 'aligning' | 'placing' | 'building_view' | 'done' | 'failed';

export interface SampleResult {
  name: string;
  placed: boolean | null;
  reason: string | null;
}

export interface Job {
  id: string;
  status: JobStatus;
  accession: string;
  organism: string;
  samples: SampleResult[];
  metadata_columns: string[];
  created_at: string;
  step_started_at: string | null;
  step_timings: Partial<Record<JobStatus, number>>;
  error: string | null;
  failed_step: JobStatus | null;
}

export interface Organism {
  key: string;
  organism: string;
  accession: string;
  leaf_count: number;
  has_example: boolean;
}

export class ApiError extends Error {
  status: number;
  errors: string[];

  constructor(status: number, errors: string[]) {
    super(errors.join('; '));
    this.status = status;
    this.errors = errors;
  }
}

async function check(res: Response): Promise<Response> {
  if (res.ok) return res;
  let errors = [`Request failed (${res.status})`];
  try {
    const body = await res.json();
    if (Array.isArray(body.errors)) errors = body.errors;
    else if (body.detail) errors = [String(body.detail)];
  } catch {
    // keep the generic message
  }
  throw new ApiError(res.status, errors);
}

export const api = {
  async createJob(fasta: File, metadata?: File | null): Promise<{ id: string }> {
    const form = new FormData();
    form.append('fasta', fasta);
    if (metadata) form.append('metadata', metadata);
    return (await check(await fetch('/api/jobs', { method: 'POST', body: form }))).json();
  },
  async getJob(id: string): Promise<Job> {
    return (await check(await fetch(`/api/jobs/${id}`))).json();
  },
  async getOrganisms(): Promise<Organism[]> {
    return (await check(await fetch('/api/organisms'))).json();
  },
  async getTree(id: string): Promise<ArrayBuffer> {
    return (await check(await fetch(`/api/jobs/${id}/tree`))).arrayBuffer();
  },
  async getExampleFile(key: string, kind: 'fasta' | 'metadata'): Promise<File | null> {
    const res = await fetch(`/api/examples/${key}/${kind}`);
    if (res.status === 404) return null;
    const name = kind === 'fasta' ? `${key}-example.fasta` : `${key}-example-metadata.tsv`;
    return new File([await (await check(res)).blob()], name);
  },
};

const FINISHED: JobStatus[] = ['done', 'failed'];

export const useOrganisms = () => useQuery({ queryKey: ['organisms'], queryFn: api.getOrganisms });

export const useJob = (id: string) =>
  useQuery({
    queryKey: ['job', id],
    queryFn: () => api.getJob(id),
    refetchInterval: (query) => (query.state.data && FINISHED.includes(query.state.data.status) ? false : 2000),
  });

export const useCreateJob = () =>
  useMutation({ mutationFn: ({ fasta, metadata }: { fasta: File; metadata?: File | null }) => api.createJob(fasta, metadata) });

export const useTree = (id: string, enabled: boolean) =>
  useQuery({ queryKey: ['tree', id], queryFn: () => api.getTree(id), enabled, staleTime: Infinity });
