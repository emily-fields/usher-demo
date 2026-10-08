import { Check, Circle, LoaderCircle, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { Job, JobStatus } from '@/lib/api';

const STEPS: { status: JobStatus; label: string }[] = [
  { status: 'aligning', label: 'Aligning to reference' },
  { status: 'placing', label: 'Placing on tree' },
  { status: 'building_view', label: 'Building tree view' },
];

function useNow() {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  return now;
}

export function JobStepper({ job }: { job: Job }) {
  const now = useNow();
  const current = job.status === 'failed' ? job.failed_step : job.status;
  const currentIndex = STEPS.findIndex((s) => s.status === current);

  return (
    <ol className="space-y-3">
      {STEPS.map((step, i) => {
        const done = job.status === 'done' || i < currentIndex || step.status in job.step_timings;
        const active = step.status === current;
        const failed = active && job.status === 'failed';
        const seconds = job.step_timings[step.status]
          ?? (active && !failed && job.step_started_at ? Math.max(0, (now - Date.parse(job.step_started_at)) / 1000) : null);
        return (
          <li key={step.status} className="flex items-center gap-3">
            {failed ? <X className="text-destructive size-5" />
              : done ? <Check className="size-5 text-green-600" />
              : active ? <LoaderCircle className="size-5 animate-spin" />
              : <Circle className="text-muted-foreground size-5" />}
            <span className={active || done ? '' : 'text-muted-foreground'}>{step.label}</span>
            {seconds !== null && <span className="text-muted-foreground ml-auto text-sm tabular-nums">{seconds.toFixed(0)}s</span>}
          </li>
        );
      })}
    </ol>
  );
}
