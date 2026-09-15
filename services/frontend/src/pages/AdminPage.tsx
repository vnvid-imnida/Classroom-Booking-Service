import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box, Paper, Typography, Tab, Tabs, Stack, Chip, Button,
  Table, TableHead, TableRow, TableCell, TableBody, TableContainer,
  Alert, CircularProgress, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, FormControlLabel, Checkbox,
} from '@mui/material';
import { bookingsApi, roomsApi } from '../api/endpoints';
import type { Booking, Room, RoomCreatePayload } from '../types';
import { STATUS_LABELS, STATUS_COLORS } from '../types';

function formatDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString('ru-RU');
  } catch {
    return iso;
  }
}

export default function AdminPage() {
  const [tab, setTab] = useState(0);

  return (
    <Box>
      <Typography variant="h1" sx={{ fontSize: '1.75rem', mb: 2 }}>
        Панель администратора
      </Typography>

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          indicatorColor="primary"
          textColor="primary"
        >
          <Tab label="Заявки на бронирование" />
          <Tab label="Аудитории" />
        </Tabs>
      </Paper>

      {tab === 0 && <BookingsTab />}
      {tab === 1 && <RoomsTab />}
    </Box>
  );
}

/* ---------- Заявки ---------- */

function BookingsTab() {
  const qc = useQueryClient();

  const bookingsQuery = useQuery<Booking[]>({
    queryKey: ['admin-bookings'],
    queryFn: () => bookingsApi.list({ admin: true }),
  });

  const approveMut = useMutation({
    mutationFn: (id: string) => bookingsApi.approve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-bookings'] }),
  });

  const rejectMut = useMutation({
    mutationFn: (id: string) => bookingsApi.reject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-bookings'] }),
  });

  if (bookingsQuery.isError) {
    return <Alert severity="warning">Не удалось загрузить список заявок.</Alert>;
  }
  if (bookingsQuery.isLoading) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  const bookings: Booking[] = bookingsQuery.data ?? [];
  const sorted = [...bookings].sort((a, b) => {
    if (a.status === 'pending' && b.status !== 'pending') return -1;
    if (b.status === 'pending' && a.status !== 'pending') return 1;
    return a.start.localeCompare(b.start);
  });

  return (
    <Paper>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Название</TableCell>
              <TableCell>Заявитель</TableCell>
              <TableCell>Аудитория</TableCell>
              <TableCell>Время</TableCell>
              <TableCell>Статус</TableCell>
              <TableCell align="right">Действия</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sorted.map((b) => {
              const isPending = b.status === 'pending';
              const busy = approveMut.isPending || rejectMut.isPending;
              return (
                <TableRow key={b.id} hover>
                  <TableCell>{b.title}</TableCell>
                  <TableCell>{b.userName ?? b.userId}</TableCell>
                  <TableCell>{b.roomNumber ?? b.roomId}</TableCell>
                  <TableCell>
                    {formatDateTime(b.start)}<br />
                    <Typography variant="caption" color="text.secondary">
                      до {formatDateTime(b.end)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={STATUS_LABELS[b.status]}
                      sx={{ bgcolor: STATUS_COLORS[b.status], color: 'white' }}
                    />
                  </TableCell>
                  <TableCell align="right">
                    {isPending ? (
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Button
                          size="small"
                          variant="contained"
                          color="success"
                          disabled={busy}
                          onClick={() => approveMut.mutate(b.id)}
                        >
                          Подтвердить
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          color="error"
                          disabled={busy}
                          onClick={() => rejectMut.mutate(b.id)}
                        >
                          Отклонить
                        </Button>
                      </Stack>
                    ) : (
                      <Typography variant="caption" color="text.secondary">—</Typography>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
            {sorted.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                    Заявок нет.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}

/* ---------- Аудитории ---------- */

function RoomsTab() {
  const qc = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);

  const roomsQuery = useQuery<Room[]>({
    queryKey: ['admin-rooms'],
    queryFn: () => roomsApi.list(),
  });

  const createMut = useMutation({
    mutationFn: (payload: RoomCreatePayload) => roomsApi.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-rooms'] });
      setDialogOpen(false);
    },
  });

  const removeMut = useMutation({
    mutationFn: (id: string) => roomsApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-rooms'] }),
  });

  if (roomsQuery.isError) {
    return <Alert severity="warning">Не удалось загрузить список аудиторий.</Alert>;
  }
  if (roomsQuery.isLoading) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  const rooms: Room[] = roomsQuery.data ?? [];

  return (
    <Paper>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 2 }}>
        <Typography variant="h6">Аудитории ({rooms.length})</Typography>
        <Button variant="contained" onClick={() => setDialogOpen(true)}>
          + Добавить аудиторию
        </Button>
      </Stack>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Номер</TableCell>
              <TableCell>Корпус</TableCell>
              <TableCell align="right">Вместимость</TableCell>
              <TableCell>Оборудование</TableCell>
              <TableCell align="right">Действия</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rooms.map((r) => (
              <TableRow key={r.id} hover>
                <TableCell>{r.number}</TableCell>
                <TableCell>{r.building}</TableCell>
                <TableCell align="right">{r.capacity}</TableCell>
                <TableCell>
                  <Stack direction="row" spacing={1}>
                    {r.hasProjector ? <Chip size="small" label="Проектор" /> : null}
                    {r.hasComputers ? <Chip size="small" label="Компьютеры" /> : null}
                  </Stack>
                </TableCell>
                <TableCell align="right">
                  <Button
                    size="small"
                    color="error"
                    variant="outlined"
                    disabled={removeMut.isPending}
                    onClick={() => removeMut.mutate(r.id)}
                  >
                    Удалить
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {rooms.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                    Аудиторий нет.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <NewRoomDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={(payload) => createMut.mutate(payload)}
        submitting={createMut.isPending}
        error={createMut.isError ? 'Не удалось создать аудиторию.' : null}
      />
    </Paper>
  );
}

function NewRoomDialog({
  open, onClose, onSubmit, submitting, error,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: RoomCreatePayload) => void;
  submitting: boolean;
  error: string | null;
}) {
  const [number, setNumber] = useState('');
  const [building, setBuilding] = useState('');
  const [capacity, setCapacity] = useState<number | ''>('');
  const [hasProjector, setHasProjector] = useState(false);
  const [hasComputers, setHasComputers] = useState(false);

  const reset = () => {
    setNumber(''); setBuilding(''); setCapacity('');
    setHasProjector(false); setHasComputers(false);
  };

  const canSubmit = !!number.trim() && !!building.trim() && typeof capacity === 'number' && capacity > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    onSubmit({
      number: number.trim(),
      building: building.trim(),
      capacity: capacity as number,
      hasProjector,
      hasComputers,
    });
  };

  return (
    <Dialog open={open} onClose={() => { onClose(); reset(); }} fullWidth maxWidth="sm">
      <form onSubmit={handleSubmit}>
        <DialogTitle>Новая аудитория</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error ? <Alert severity="error">{error}</Alert> : null}
            <TextField
              label="Номер аудитории"
              value={number}
              onChange={(e) => setNumber(e.target.value)}
              required
              autoFocus
              fullWidth
            />
            <TextField
              label="Корпус"
              value={building}
              onChange={(e) => setBuilding(e.target.value)}
              required
              fullWidth
            />
            <TextField
              type="number"
              label="Вместимость"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value ? +e.target.value : '')}
              inputProps={{ min: 1 }}
              required
              fullWidth
            />
            <FormControlLabel
              control={<Checkbox checked={hasProjector} onChange={(e) => setHasProjector(e.target.checked)} />}
              label="Проектор"
            />
            <FormControlLabel
              control={<Checkbox checked={hasComputers} onChange={(e) => setHasComputers(e.target.checked)} />}
              label="Компьютеры"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { onClose(); reset(); }}>Отмена</Button>
          <Button type="submit" variant="contained" disabled={!canSubmit || submitting}>
            {submitting ? 'Создание...' : 'Создать'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
