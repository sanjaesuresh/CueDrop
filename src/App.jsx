import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

const AdminApp = lazy(() => import('./admin/App.jsx'));
const GuestApp = lazy(() => import('./guest/App.jsx'));

function Loading() {
  return (
    <div className="flex items-center justify-center h-screen bg-gray-900 text-white">
      <div className="animate-pulse text-xl">Loading...</div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/admin/*" element={<AdminApp />} />
          <Route path="/guest/:sessionId" element={<GuestApp />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
