import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box, Paper, Typography, Stack, Avatar, Divider, Chip, Button,
  List, ListItem, ListItemText, Alert, CircularProgress,
} from '@mui/material';
import { useAuth } from '../auth/AuthContext';
import { bookingsApi } from '../api/endpoints';
import type { Booking } from '../types';
import { STATUS_LABELS, STATUS_COLORS, ROLE_LABELS } from '../types';

function getInitials(user: { fullName?: string; email: string }): string {
  const source = (user.fullName && user.fullName.trim()) || user.email || '?';
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  const letters = parts.slice(0, 2).map((p) => p[0] ?? '').join('');
  return letters.toUpperCase() || '?';
}

function formatRange(start: string, end: string): string {
  try {
    const s = new Date(start);
    const e = new Date(end);
    if (isNaN(s.getTime()) || isNaN(e.getTime())) return `${start} — ${end}`;
    return `${s.toLocaleString('ru-RU')} — ${e.toLocaleString('ru-RU')}`;
  } catch {
    return `${start} — ${end}`;
  }
}

export default function AccountPage() {
  const { user, logout } = useAuth();
  const qc = useQueryClient();

  const bookingsQuery = useQuery<Booking[]>({
    queryKey: ['my-bookings', user?.id ?? ''],
    queryFn: () => bookingsApi.list(user?.id ? { userId: user.id } : undefined),
    enabled: !!user,
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => bookingsApi.cancel(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['my-bookings'] });
    },
  });

  if (!user) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  const bookings: Booking[] = bookingsQuery.data ?? [];

  return (
    <Box>
      <Typography variant="h1" sx={{ fontSize: '1.75rem', mb: 2 }}>
        Личный кабинет
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={3} alignItems="center">
          <Avatar sx={{ width: 72, height: 72, bgcolor: 'primary.main', fontSize: 24 }}>
            {getInitials(user)}
          </Avatar>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6">{user.fullName || 'Пользователь'}</Typography>
            <Typography variant="body2" color="text.secondary">{user.email}</Typography>
            <Chip
              size="small"
              label={ROLE_LABELS[user.role] ?? user.role}
              sx={{ mt: 1 }}
            />
          </Box>
          <Button variant="outlined" onClick={logout}>Выйти</Button>
        </Stack>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Мои бронирования</Typography>
        <Divider sx={{ mb: 1 }} />

        {bookingsQuery.isError && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            Не удалось загрузить ваши бронирования.
          </Alert>
        )}

        {bookingsQuery.isLoading && (
          <Box display="flex" justifyContent="center" py={2}>
            <CircularProgress size={24} />
          </Box>
        )}

        {!bookingsQuery.isLoading && !bookingsQuery.isError && bookings.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            У вас пока нет бронирований.
          </Typography>
        )}

        <List>
          {bookings.map((b) => {
            const canCancel = b.status !== 'cancelled' && b.status !== 'rejected';
            return (
              <ListItem
                key={b.id}
                sx={{ alignItems: 'flex-start', py: 1.5 }}
                divider
              >
                <ListItemText
                  primary={
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                      <Typography variant="subtitle1" component="span">
                        {b.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" component="span">
                        — ауд. {b.roomNumber ?? b.roomId}
                      </Typography>
                      <Chip
                        size="small"
                        label={STATUS_LABELS[b.status]}
                        sx={{ bgcolor: STATUS_COLORS[b.status], color: 'white' }}
                      />
                    </Stack>
                  }
                  secondary={formatRange(b.start, b.end)}
                />
                {canCancel ? (
                  <Button
                    size="small"
                    color="error"
                    variant="outlined"
                    onClick={() => cancelMutation.mutate(b.id)}
                    disabled={cancelMutation.isPending}
                    sx={{ ml: 2, flexShrink: 0 }}
                  >
                    Отменить
                  </Button>
                ) : null}
              </ListItem>
            );
          })}
        </List>
      </Paper>
    </Box>
  );
}
