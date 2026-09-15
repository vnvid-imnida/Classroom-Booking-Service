import { Navigate } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import { useAuth } from '../auth/AuthContext';

/** SPA fallback: unknown paths → login or schedule (not a blank 404). */
export default function CatchAllRedirect() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/schedule" replace />;
  }

  return <Navigate to="/login" replace />;
}
