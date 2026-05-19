import { useState } from 'react';
import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import {
  Box, Paper, TextField, Button, Typography, Alert, Stack, Link, Divider,
} from '@mui/material';
import { useAuth } from '../auth/AuthContext';
import { TEST_EMAIL, TEST_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD } from '../api/mock';

export default function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/schedule';
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate('/schedule', { replace: true });
    } catch (err) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        (err as Error)?.message ||
        'Не удалось войти. Проверьте email и пароль.';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const useUser  = () => { setEmail(TEST_EMAIL);  setPassword(TEST_PASSWORD);  setError(null); };
  const useAdmin = () => { setEmail(ADMIN_EMAIL); setPassword(ADMIN_PASSWORD); setError(null); };

  return (
    <Box display="flex" justifyContent="center" alignItems="center" minHeight="70vh">
      <Paper elevation={3} sx={{ p: 4, width: '100%', maxWidth: 460 }}>
        <Typography variant="h1" sx={{ fontSize: '1.75rem', mb: 1 }}>
          Вход в систему
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Введите учётные данные СПбПУ
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <form onSubmit={handleSubmit}>
          <Stack spacing={2}>
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              fullWidth
            />
            <TextField
              label="Пароль"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              fullWidth
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={submitting || isLoading}
            >
              {submitting ? 'Входим...' : 'Войти'}
            </Button>
            <Link href="#" variant="body2" sx={{ textAlign: 'center' }}>
              Забыли пароль?
            </Link>
          </Stack>
        </form>

        <Divider sx={{ my: 3 }}>Демо-режим</Divider>
        <Alert
          severity="info"
          action={
            <Stack direction="row" spacing={1}>
              <Button color="inherit" size="small" onClick={useUser}>Студент</Button>
              <Button color="inherit" size="small" onClick={useAdmin}>Админ</Button>
            </Stack>
          }
        >
          Для просмотра без backend:
          <br />
          <strong>{TEST_EMAIL}</strong> / <strong>{TEST_PASSWORD}</strong>
          <br />
          <strong>{ADMIN_EMAIL}</strong> / <strong>{ADMIN_PASSWORD}</strong>
        </Alert>
      </Paper>
    </Box>
  );
}
