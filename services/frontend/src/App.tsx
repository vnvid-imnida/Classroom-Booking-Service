import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import CatchAllRedirect from './components/CatchAllRedirect';
import SchedulePage from './pages/SchedulePage';
import SearchPage from './pages/SearchPage';
import AccountPage from './pages/AccountPage';
import AdminPage from './pages/AdminPage';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import RoleProtectedRoute from './components/RoleProtectedRoute';
import { AuthProvider } from './auth/AuthContext';
import { ADMIN_ROLES } from './types';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/schedule" element={<SchedulePage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/account" element={<AccountPage />} />
              <Route element={<RoleProtectedRoute allow={ADMIN_ROLES} />}>
                <Route path="/admin" element={<AdminPage />} />
              </Route>
              <Route path="/" element={<Navigate to="/schedule" replace />} />
            </Route>
          </Route>
          <Route path="*" element={<CatchAllRedirect />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
