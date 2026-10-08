import { Route, Routes } from 'react-router';
import { AppHeader } from '@/components/app-header';
import JobPage from '@/features/job/job-page';
import UploadPage from '@/features/upload/upload-page';

export default function App() {
  return (
    <div className="bg-background text-foreground min-h-screen">
      <AppHeader />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/jobs/:id" element={<JobPage />} />
        </Routes>
      </main>
    </div>
  );
}
