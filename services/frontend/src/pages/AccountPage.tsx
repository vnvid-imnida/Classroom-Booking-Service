import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box, Paper, Typography, Stack, Avatar, Divider, Chip, Button,
  List, ListItem, ListItemText, Alert, CircularProgress, Tabs, Tab,
  Dialog, DialogTitle, DialogContent, DialogActions,
} from '@mui/material';
import { useAuth } from '../auth/AuthContext';
import { bookingsApi } from '../api/endpoints';
import type { Booking } from '../types';
import { STATUS_LABELS, STATUS_COLORS, ROLE_LABELS } from '../types';
import { formatMoscowRange } from '../utils/dateTime';
import { getErrorDetail } from '../utils/apiError';

function cancelErrorRu(detail: string | undefined): string | null {
  if (!detail) return null;
  if (detail.includes('24 hours')) {
    return 'Отмена возможна только более чем за 24 часа до начала';
  }
  if (detail.startsWith('Only draft or pending')) {
    return 'Эту заявку уже нельзя отменить';
  }
  if (detail === 'Only active bookings can be cancelled') {
    return 'Отменить можно только активное бронирование';
  }
  return detail;
}

function getInitials(user: { fullName?: string; email: string }): string {
  const source = (user.fullName && user.fullName.trim()) || user.email || '?';
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  const letters = parts.slice(0, 2).map((p) => p[0] ?? '').join('');
  return letters.toUpperCase() || '?';
}

function canCancel(item: Booking, scope: 'active' | 'archive'): boolean {
  if (scope !== 'active') return false;
  if (item.kind === 'request') {
    return item.status === 'draft' || item.status === 'pending';
  }
  return item.status === 'approved';
}

function kindLabel(item: Booking): string {
  return item.kind === 'request' ? 'Заявка' : 'Бронь';
}

export default function AccountPage() {
  const { user, logout } = useAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState(0);
  const [confirmCancel, setConfirmCancel] = useState<Booking | null>(null);
  const scope: 'active' | 'archive' = tab === 0 ? 'active' : 'archive';

  const bookingsQuery = useQuery<Booking[]>({
    queryKey: ['my-bookings', user?.id ?? '', scope],
    queryFn: () => bookingsApi.list({ scope }),
    enabled: !!user,
  });

  const cancelMutation = useMutation({
    mutationFn: (item: Booking) => bookingsApi.cancel(item),
    onSuccess: () => {
      setConfirmCancel(null);
      qc.invalidateQueries({ queryKey: ['my-bookings'] });
      qc.invalidateQueries({ queryKey: ['bookings'] });
    },
  });

  if (!user) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  const items = [...(bookingsQuery.data ?? [])].sort((a, b) =>
    a.start.localeCompare(b.start),
  );

  const cancelError = cancelMutation.isError
    ? cancelErrorRu(getErrorDetail(cancelMutation.error)) ?? 'Не удалось отменить.'
    : null;

  const confirmKind =
    confirmCancel?.kind === 'request' ? 'заявку' : 'бронирование';

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
        <Typography variant="h6" sx={{ mb: 1 }}>Мои бронирования</Typography>
        <Tabs
          value={tab}
          onChange={(_, v: number) => {
            setTab(v);
            cancelMutation.reset();
            setConfirmCancel(null);
          }}
          sx={{ mb: 1 }}
        >
          <Tab label="Активные" />
          <Tab label="Архив" />
        </Tabs>
        <Divider sx={{ mb: 1 }} />

        {cancelError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => cancelMutation.reset()}>
            {cancelError}
          </Alert>
        )}

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

        {!bookingsQuery.isLoading && !bookingsQuery.isError && items.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            {scope === 'active'
              ? 'Нет активных заявок и бронирований.'
              : 'Архив пуст.'}
          </Typography>
        )}

        <List>
          {items.map((b) => (
            <ListItem
              key={`${b.kind}-${b.id}`}
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
                    <Chip size="small" variant="outlined" label={kindLabel(b)} />
                    <Chip
                      size="small"
                      label={STATUS_LABELS[b.status]}
                      sx={{ bgcolor: STATUS_COLORS[b.status], color: 'white' }}
                    />
                  </Stack>
                }
                secondary={formatMoscowRange(b.start, b.end)}
              />
              {canCancel(b, scope) ? (
                <Button
                  size="small"
                  color="error"
                  variant="outlined"
                  onClick={() => {
                    cancelMutation.reset();
                    setConfirmCancel(b);
                  }}
                  disabled={cancelMutation.isPending}
                  sx={{ ml: 2, flexShrink: 0 }}
                >
                  Отменить
                </Button>
              ) : null}
            </ListItem>
          ))}
        </List>
      </Paper>

      <Dialog
        open={!!confirmCancel}
        onClose={cancelMutation.isPending ? undefined : () => setConfirmCancel(null)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Отмена</DialogTitle>
        <DialogContent>
          <Typography>
            Вы точно хотите отменить {confirmKind}
            {confirmCancel ? <> «{confirmCancel.title}»?</> : '?'}
          </Typography>
          {confirmCancel && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Ауд. {confirmCancel.roomNumber ?? confirmCancel.roomId}
              {' · '}
              {formatMoscowRange(confirmCancel.start, confirmCancel.end)}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setConfirmCancel(null)}
            disabled={cancelMutation.isPending}
          >
            Нет
          </Button>
          <Button
            color="error"
            variant="contained"
            disabled={!confirmCancel || cancelMutation.isPending}
            onClick={() => {
              if (confirmCancel) cancelMutation.mutate(confirmCancel);
            }}
          >
            {cancelMutation.isPending ? 'Отмена…' : 'Да, отменить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
