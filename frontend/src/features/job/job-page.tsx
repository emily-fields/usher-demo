import { AlertCircle, LoaderCircle } from 'lucide-react';
import { Link, useParams } from 'react-router';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TaxoniumViewer } from '@/features/tree/taxonium-viewer';
import { useJob } from '@/lib/api';
import { JobStepper } from './job-stepper';
import { SamplePanel } from './sample-panel';

export default function JobPage() {
  const { id = '' } = useParams();
  const job = useJob(id);

  if (job.isPending) return <LoaderCircle className="mx-auto size-8 animate-spin" />;
  // A failed poll keeps the last good data, so only show "not found" when there is none.
  if (!job.data) {
    return (
      <Alert variant="destructive" className="mx-auto max-w-xl">
        <AlertCircle className="size-4" />
        <AlertTitle>Job not found</AlertTitle>
        <AlertDescription><Link className="underline" to="/">Start a new placement</Link></AlertDescription>
      </Alert>
    );
  }

  const data = job.data;
  if (data.status === 'done') {
    return (
      <div className="grid gap-4 lg:grid-cols-[1fr_18rem]">
        <TaxoniumViewer jobId={data.id} />
        <SamplePanel job={data} />
      </div>
    );
  }

  return (
    <Card className="mx-auto max-w-xl">
      <CardHeader>
        <CardTitle>Placing {data.samples.length} sample{data.samples.length === 1 ? '' : 's'} on {data.organism}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <JobStepper job={data} />
        {data.status === 'failed' && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertTitle>Placement failed</AlertTitle>
            <AlertDescription>
              <p>{data.error}</p>
              <Button asChild variant="outline" size="sm" className="mt-2"><Link to="/">Try again</Link></Button>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
