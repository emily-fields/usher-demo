import { Link } from 'react-router';
import { Network } from 'lucide-react';

export function AppHeader() {
  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <Network className="size-5" />
          UShER Placement Demo
        </Link>
        <p className="text-muted-foreground text-xs">
          Placement by{' '}
          <a className="underline" href="https://github.com/yatisht/usher" target="_blank" rel="noreferrer">UShER</a>
          , visualized with{' '}
          <a className="underline" href="https://taxonium.org" target="_blank" rel="noreferrer">Taxonium</a>
        </p>
      </div>
    </header>
  );
}
