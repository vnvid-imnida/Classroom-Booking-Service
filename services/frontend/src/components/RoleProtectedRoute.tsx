import { Navigate, Outlet } from 'react-router-dom';
import { Box, Alert } from '@mui/material';
import { useAuth } from '../auth/AuthContext';
import type { UserRole } from '../types';

interface Props {
  allow: UserRole[];
}

export default function RoleProtectedRoute({ allow }: Props) {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;

  if (!allow.includes(user.role)) {
    return (
      <Box sx={{ py: 4 }}>
        <Alert severity="error">
          Доступ запрещён: у вашей роли недостаточно прав для этой страницы.
        </Alert>
      </Box>
    );
  }

  return <Outlet />;
}
