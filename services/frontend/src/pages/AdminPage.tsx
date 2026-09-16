import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box, Paper, Typography, Tab, Tabs, Stack, Chip, Button,
  Table, TableHead, TableRow, TableCell, TableBody, TableContainer,
  Alert, CircularProgress, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, FormControlLabel, Checkbox, FormControl, InputLabel, Select, MenuItem,
} from '@mui/material';
import { bookingsApi, buildingsApi, roomsApi } from '../api/endpoints';
import type { Booking, Room, RoomCreatePayload } from '../types';
import { STATUS_LABELS, STATUS_COLORS } from '../types';
import { formatMoscowDateTime } from '../utils/dateTime';
import { getErrorDetail } from '../utils/apiError';

function formatDateTime(iso: string): string {
  return formatMoscowDateTime(iso);
}

function roomApiErrorRu(detail: string | undefined, fallback: string): string {
  if (!detail) return fallback;
  if (detail.includes('already exists')) {
    return 'Аудитория с таким номером уже есть в этом корпусе.';
  }
  if (detail.includes('Building not found')) {
    return 'Корпус не найден. Выберите корпус из списка.';
  }
  if (detail.includes('Moderator role')) {
    return 'Нужна роль модератора или администратора.';
  }
  if (detail === 'Room not found') {
    return 'Аудитория не найдена или уже удалена.';
  }
  return detail;
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
  const [confirmDelete, setConfirmDelete] = useState<Room | null>(null);

  const roomsQuery = useQuery<Room[]>({
    queryKey: ['admin-rooms'],
    queryFn: () => roomsApi.list(),
  });

  const invalidateRooms = () => {
    qc.invalidateQueries({ queryKey: ['admin-rooms'] });
    qc.invalidateQueries({ queryKey: ['rooms'] });
  };

  const createMut = useMutation({
    mutationFn: (payload: RoomCreatePayload) => roomsApi.create(payload),
    onSuccess: () => {
      invalidateRooms();
      setDialogOpen(false);
    },
  });

  const removeMut = useMutation({
    mutationFn: (id: string) => roomsApi.remove(id),
    onSuccess: () => {
      setConfirmDelete(null);
      invalidateRooms();
    },
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
  const removeError = removeMut.isError
    ? roomApiErrorRu(getErrorDetail(removeMut.error), 'Не удалось удалить аудиторию.')
    : null;

  return (
    <Paper>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 2 }}>
        <Typography variant="h6">Аудитории ({rooms.length})</Typography>
        <Button
          variant="contained"
          onClick={() => {
            createMut.reset();
            setDialogOpen(true);
          }}
        >
          + Добавить аудиторию
        </Button>
      </Stack>

      {removeError && (
        <Alert severity="error" sx={{ mx: 2, mb: 1 }} onClose={() => removeMut.reset()}>
          {removeError}
        </Alert>
      )}

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
                    {r.hasWhiteboard ? <Chip size="small" label="Доска" /> : null}
                  </Stack>
                </TableCell>
                <TableCell align="right">
                  <Button
                    size="small"
                    color="error"
                    variant="outlined"
                    disabled={removeMut.isPending}
                    onClick={() => {
                      removeMut.reset();
                      setConfirmDelete(r);
                    }}
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
        error={
          createMut.isError
            ? roomApiErrorRu(getErrorDetail(createMut.error), 'Не удалось создать аудиторию.')
            : null
        }
      />

      <Dialog
        open={!!confirmDelete}
        onClose={removeMut.isPending ? undefined : () => setConfirmDelete(null)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Удаление аудитории</DialogTitle>
        <DialogContent>
          <Typography>
            Вы точно хотите удалить аудиторию
            {confirmDelete ? <> «{confirmDelete.number}» ({confirmDelete.building})?</> : '?'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Аудитория исчезнет из поиска; связанные заявки и брони в истории сохранятся.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDelete(null)} disabled={removeMut.isPending}>
            Нет
          </Button>
          <Button
            color="error"
            variant="contained"
            disabled={!confirmDelete || removeMut.isPending}
            onClick={() => {
              if (confirmDelete) removeMut.mutate(confirmDelete.id);
            }}
          >
            {removeMut.isPending ? 'Удаление…' : 'Да, удалить'}
          </Button>
        </DialogActions>
      </Dialog>
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
  const [buildingCode, setBuildingCode] = useState('');
  const [capacity, setCapacity] = useState<number | ''>('');
  const [hasProjector, setHasProjector] = useState(false);
  const [hasWhiteboard, setHasWhiteboard] = useState(false);
  const [isAccessible, setIsAccessible] = useState(false);

  const buildingsQuery = useQuery({
    queryKey: ['buildings'],
    queryFn: () => buildingsApi.list(),
    enabled: open,
  });

  const reset = () => {
    setNumber('');
    setBuildingCode('');
    setCapacity('');
    setHasProjector(false);
    setHasWhiteboard(false);
    setIsAccessible(false);
  };

  const canSubmit =
    !!number.trim() &&
    !!buildingCode &&
    typeof capacity === 'number' &&
    capacity > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    const building = (buildingsQuery.data ?? []).find((b) => b.code === buildingCode);
    onSubmit({
      number: number.trim(),
      building: building?.name ?? buildingCode,
      buildingCode,
      capacity: capacity as number,
      hasProjector,
      hasWhiteboard,
      isAccessible,
    });
  };

  const handleClose = () => {
    onClose();
    reset();
  };

  return (
    <Dialog open={open} onClose={submitting ? undefined : handleClose} fullWidth maxWidth="sm">
      <form onSubmit={handleSubmit}>
        <DialogTitle>Новая аудитория</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error ? <Alert severity="error">{error}</Alert> : null}
            {buildingsQuery.isError && (
              <Alert severity="warning">Не удалось загрузить корпуса.</Alert>
            )}
            <TextField
              label="Номер аудитории"
              value={number}
              onChange={(e) => setNumber(e.target.value)}
              required
              autoFocus
              fullWidth
              helperText="Этаж возьмём из первой цифры номера, если не указать иначе"
            />
            <FormControl fullWidth required>
              <InputLabel id="new-room-building">Корпус</InputLabel>
              <Select
                labelId="new-room-building"
                label="Корпус"
                value={buildingCode || 'none'}
                onChange={(e) =>
                  setBuildingCode(e.target.value === 'none' ? '' : e.target.value)
                }
              >
                <MenuItem value="none" disabled>
                  Выберите корпус
                </MenuItem>
                {(buildingsQuery.data ?? []).map((b) => (
                  <MenuItem key={b.code} value={b.code}>
                    {b.name} ({b.code})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
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
              control={<Checkbox checked={hasWhiteboard} onChange={(e) => setHasWhiteboard(e.target.checked)} />}
              label="Доска"
            />
            <FormControlLabel
              control={<Checkbox checked={isAccessible} onChange={(e) => setIsAccessible(e.target.checked)} />}
              label="Доступна для маломобильных"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={submitting}>Отмена</Button>
          <Button type="submit" variant="contained" disabled={!canSubmit || submitting}>
            {submitting ? 'Создание...' : 'Создать'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
