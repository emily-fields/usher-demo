import { ListTree, LoaderCircle, Maximize2, Minimize2 } from 'lucide-react';
import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { useTree } from '@/lib/api';

// @ts-expect-error - taxonium-component ships no types
const TaxoniumTreeViewer = lazy(() => import('taxonium-component'));

type Query = Record<string, unknown>;

// Highlights every uploaded sample via the placed_sample metadata column added by the backend.
const PLACED_QUERY: Query = {
  srch: JSON.stringify([{ key: 'placed', type: 'meta_placed_sample', method: 'text_exact', text: 'yes' }]),
  enabled: JSON.stringify({ placed: true }),
  zoomToSearch: 0,
};

function Loading() {
  return <LoaderCircle className="text-muted-foreground size-8 animate-spin" />;
}

export function TaxoniumViewer({ jobId }: { jobId: string }) {
  const tree = useTree(jobId, true);
  const container = useRef<HTMLDivElement>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [query, setQuery] = useState<Query>(PLACED_QUERY);
  const updateQuery = useCallback((partial: Query) => setQuery((prev) => ({ ...prev, ...partial })), []);

  useEffect(() => {
    const onChange = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);

  const toggleFullscreen = () =>
    document.fullscreenElement ? document.exitFullscreen() : container.current?.requestFullscreen();

  return (
    <div ref={container} className="bg-background flex h-[75vh] flex-col overflow-hidden rounded-lg border">
      <div className="flex items-center justify-between border-b px-3 py-1.5">
        <span className="flex items-center gap-2 text-sm font-medium">
          <ListTree className="size-4" /> Phylogenetic tree
        </span>
        <Button variant="ghost" size="sm" onClick={toggleFullscreen}>
          {fullscreen ? <Minimize2 className="size-4" /> : <Maximize2 className="size-4" />}
          {fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        </Button>
      </div>
      <div className="flex flex-1 items-center justify-center overflow-hidden">
        {tree.isError ? (
          <p className="text-muted-foreground">Unable to load the tree.</p>
        ) : !tree.data ? (
          <Loading />
        ) : (
          <Suspense fallback={<Loading />}>
            <div className="h-full w-full">
              <TaxoniumTreeViewer
                sourceData={{ status: 'loaded', filename: 'tree.jsonl.gz', data: tree.data, filetype: 'jsonl' }}
                query={query}
                updateQuery={updateQuery}
              />
            </div>
          </Suspense>
        )}
      </div>
    </div>
  );
}
