import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
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
import { REGISTER_EXISTS_WEB_HINT_RU } from '../utils/authMessages';
import {
  DOMAIN_ERROR_RU,
  roleLabelForEmail,
  validateSpbstuEmail,
} from '../utils/emailDomains';

export default function RegisterPage() {
  const { register, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const roleHint = roleLabelForEmail(email);

  if (isAuthenticated) {
    return <Navigate to="/schedule" replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const domainCheck = validateSpbstuEmail(email);
    if (!domainCheck.ok) {
      setError(domainCheck.message);
      return;
    }
    if (password.length < 6) {
      setError('Пароль должен быть не короче 6 символов.');
      return;
    }
    if (!fullName.trim()) {
      setError('Укажите ФИО.');
      return;
    }
    setSubmitting(true);
    try {
      await register(email, password, fullName.trim());
      navigate('/schedule', { replace: true });
    } catch (err) {
      const status = getErrorStatus(err);
      const detail = getErrorDetail(err);
      if (status === 409) {
        setError(detail ?? REGISTER_EXISTS_WEB_HINT_RU);
      } else if (status === 400) {
        setError(detail ?? DOMAIN_ERROR_RU);
      } else {
        setError(
          detail ?? 'Не удалось зарегистрироваться. Попробуйте позже.',
        );
      }
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
          {DOMAIN_ERROR_RU}
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <form onSubmit={handleSubmit}>
          <Stack spacing={2}>
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@spbstu.ru"
              required
              autoFocus
              fullWidth
              helperText={
                roleHint
                  ? `Роль: ${roleHint} (@edu.spbstu.ru — студент, @spbstu.ru — преподаватель)`
                  : 'Только @spbstu.ru и @edu.spbstu.ru'
              }
            />
            <TextField
              label="ФИО"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              fullWidth
            />
            <TextField
              label="Пароль"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              fullWidth
              helperText="Минимум 6 символов"
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
