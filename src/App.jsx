import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

const Landing  = lazy(() => import('./Landing.jsx'));
const AdminApp = lazy(() => import('./admin/App.jsx'));
const GuestApp = lazy(() => import('./guest/App.jsx'));

function Loading() {
  return (
    <div className="flex items-center justify-center h-screen bg-deep text-white">
      <div className="animate-pulse text-xl" style={{ fontFamily: 'var(--font-mono)' }}>
        Loading...
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/admin/*" element={<AdminApp />} />
          <Route path="/guest/:sessionId" element={<GuestApp />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
