import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { BatchListPage } from '@/pages/BatchListPage';
import { BatchImportPage } from '@/pages/BatchImportPage';
import { BatchDetailPage } from '@/pages/BatchDetailPage';
import './styles.css';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<BatchListPage />} />
          <Route path="import" element={<BatchImportPage />} />
          <Route path="batches/:id" element={<BatchDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
