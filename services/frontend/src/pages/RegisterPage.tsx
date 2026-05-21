import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import {
  Box, Paper, TextField, Button, Typography, Alert, Stack,
} from '@mui/material';
import { useAuth } from '../auth/AuthContext';
import { getApiErrorMessage } from '../utils/apiError';

export default function RegisterPage() {
  const { register, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isLoading) {
    return null;
  }

  if (isAuthenticated) {
    const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/schedule';
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(email, password, fullName);
      navigate('/schedule', { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err, 'Не удалось зарегистрироваться. Проверьте данные.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box display="flex" justifyContent="center" alignItems="center" minHeight="70vh">
      <Paper elevation={3} sx={{ p: 4, width: '100%', maxWidth: 460 }}>
        <Typography variant="h1" sx={{ fontSize: '1.75rem', mb: 1 }}>
          Регистрация
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Учётная запись для бронирования аудиторий СПбПУ. После регистрации войдите в Telegram-боте: /login
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <form onSubmit={handleSubmit}>
          <Stack spacing={2}>
            <TextField
              label="ФИО"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              autoFocus
              fullWidth
            />
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              fullWidth
            />
            <TextField
              label="Пароль"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              helperText="Минимум 6 символов"
              inputProps={{ minLength: 6 }}
              fullWidth
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={submitting || isLoading}
            >
              {submitting ? 'Регистрируем...' : 'Зарегистрироваться'}
            </Button>
            <Typography variant="body2" sx={{ textAlign: 'center' }}>
              Уже есть аккаунт?{' '}
              <Link to="/login">Войти</Link>
            </Typography>
          </Stack>
        </form>
      </Paper>
    </Box>
  );
}
