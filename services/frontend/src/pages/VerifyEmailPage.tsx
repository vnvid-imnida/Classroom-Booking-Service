import { useState } from 'react';
import { Link as RouterLink, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useAuth } from '../auth/AuthContext';
import { getErrorDetail, getErrorStatus } from '../utils/apiError';

export default function VerifyEmailPage() {
  const { verifyEmail, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const email = searchParams.get('email')?.trim().toLowerCase() || '';

  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/schedule" replace />;
  }

  if (!email) {
    return <Navigate to="/register" replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!/^\d{6}$/.test(code)) {
      setError('Введите 6-значный код из письма.');
      return;
    }
    setSubmitting(true);
    try {
      await verifyEmail(email, code);
      navigate('/schedule', { replace: true });
    } catch (err) {
      const status = getErrorStatus(err);
      const detail = getErrorDetail(err);
      if (status === 404) {
        setError('Пользователь не найден. Зарегистрируйтесь снова.');
      } else {
        setError(detail ?? 'Не удалось подтвердить email. Проверьте код.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box display="flex" justifyContent="center" alignItems="center" minHeight="70vh">
      <Paper elevation={3} sx={{ p: 4, width: '100%', maxWidth: 460 }}>
        <Typography variant="h1" sx={{ fontSize: '1.75rem', mb: 1 }}>
          Подтверждение email
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Мы отправили 6-значный код на <strong>{email}</strong>.
          {import.meta.env.DEV && (
            <>
              {' '}
              При локальной разработке код также пишется в лог backend (если{' '}
              <code>EMAIL_ENABLED=false</code>).
            </>
          )}
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <form onSubmit={handleSubmit}>
          <Stack spacing={2}>
            <TextField
              label="Код из письма"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              inputMode="numeric"
              autoComplete="one-time-code"
              required
              autoFocus
              fullWidth
              placeholder="123456"
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={submitting || isLoading || code.length !== 6}
            >
              {submitting ? 'Проверяем...' : 'Подтвердить'}
            </Button>
            <Typography variant="body2" sx={{ textAlign: 'center' }}>
              Уже подтвердили? <RouterLink to="/login">Войти</RouterLink>
            </Typography>
            <Typography variant="body2" sx={{ textAlign: 'center' }}>
              <RouterLink to="/register">Зарегистрироваться заново</RouterLink>
            </Typography>
          </Stack>
        </form>
      </Paper>
    </Box>
  );
}
