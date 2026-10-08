import { Link2, Plus } from 'lucide-react';
import { Link } from 'react-router';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Job } from '@/lib/api';

export function SamplePanel({ job }: { job: Job }) {
  const placed = job.samples.filter((s) => s.placed).length;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{job.organism}</CardTitle>
        <p className="text-muted-foreground text-sm">{placed} of {job.samples.length} placed</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="max-h-80 space-y-2 overflow-auto text-sm">
          {job.samples.map((s) => (
            <li key={s.name} className="flex flex-col">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-mono">{s.name}</span>
                {s.placed ? <Badge>placed</Badge> : <Badge variant="destructive">not placed</Badge>}
              </div>
              {s.reason && <span className="text-muted-foreground text-xs">{s.reason}</span>}
            </li>
          ))}
        </ul>
        <div className="flex flex-col gap-2">
          <Button variant="outline" onClick={() => navigator.clipboard.writeText(window.location.href).then(() => toast.success('Link copied'))}>
            <Link2 className="size-4" /> Copy share link
          </Button>
          <Button asChild>
            <Link to="/"><Plus className="size-4" /> Place another</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
