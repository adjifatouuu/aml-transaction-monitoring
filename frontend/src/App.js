import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import AlertesPage from './pages/AlertesPage';
import InvestigationPage from './pages/InvestigationPage';
import DashboardPage from './pages/DashboardPage';
import ParametresPage from './pages/ParametresPage';

export default function App() {
  return (
    <BrowserRouter>
      <MainLayout>
        <Routes>
          <Route path="/" element={<Navigate to="/alertes" replace />} />
          <Route path="/alertes" element={<AlertesPage />} />
          <Route path="/investigation/:id?" element={<InvestigationPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/parametres" element={<ParametresPage />} />
        </Routes>
      </MainLayout>
    </BrowserRouter>
  );
}
