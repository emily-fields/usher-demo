import { FileUp, X } from 'lucide-react';
import { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface Props {
  label: string;
  hint: string;
  accept: string;
  file: File | null;
  onFile: (file: File | null) => void;
}

export function FileDropZone({ label, hint, accept, file, onFile }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center transition-colors',
        dragging ? 'border-primary bg-muted' : 'border-border',
      )}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const dropped = e.dataTransfer.files[0];
        if (dropped) onFile(dropped);
      }}
    >
      <FileUp className="text-muted-foreground size-6" />
      <p className="font-medium">{label}</p>
      {file ? (
        <div className="flex items-center gap-2 text-sm">
          <span className="font-mono">{file.name}</span>
          <Button variant="ghost" size="icon" aria-label={`Remove ${label}`} onClick={() => onFile(null)}>
            <X className="size-4" />
          </Button>
        </div>
      ) : (
        <>
          <p className="text-muted-foreground text-sm">{hint}</p>
          <Button variant="outline" size="sm" onClick={() => input.current?.click()}>Choose file</Button>
        </>
      )}
      <input
        ref={input}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => { onFile(e.target.files?.[0] ?? null); e.target.value = ''; }}
      />
    </div>
  );
}
