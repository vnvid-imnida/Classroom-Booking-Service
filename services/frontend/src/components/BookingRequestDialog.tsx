import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle,
  FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { bookingsApi, purposesApi, roomsApi } from '../api/endpoints';
import type { Room } from '../types';
import { freeRuzSlots, isMoscowSunday, moscowDateTimeToUtcIso, RUZ_TIME_SLOTS } from '../utils/dateTime';
import { getErrorDetail } from '../utils/apiError';

const SUNDAY_BOOKING_HINT = 'В воскресенье бронирование недоступно (выходной).';

function bookingErrorRu(detail: string | undefined): string {
  if (!detail) return 'Не удалось отправить заявку.';
  if (detail.toLowerCase().includes('sunday')) {
    return SUNDAY_BOOKING_HINT;
  }
  if (detail.includes('not available')) {
    return 'Аудитория уже занята в выбранный интервал. Выберите другое время.';
  }
  if (detail.includes('ends_at must be after')) {
    return 'Время окончания должно быть позже начала.';
  }
  if (detail.startsWith('Cannot submit')) {
    return 'Заявку в этом статусе нельзя отправить на модерацию.';
  }
  return detail;
}

type Props = {
  open: boolean;
  room: Room | null;
  initialDate?: string;
  /** Prefill from search filters, e.g. ``08:00 — 09:40``. */
  initialSlotLabel?: string;
  onClose: () => void;
};

export default function BookingRequestDialog({
  open,
  room,
  initialDate,
  initialSlotLabel,
  onClose,
}: Props) {
  const qc = useQueryClient();
  const [date, setDate] = useState('');
  const [slotKey, setSlotKey] = useState('');
  const [purposeId, setPurposeId] = useState<number | ''>('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDate(initialDate ?? '');
    const fromLabel = initialSlotLabel
      ? RUZ_TIME_SLOTS.find((s) => s.label === initialSlotLabel)
      : undefined;
    setSlotKey(fromLabel ? `${fromLabel.start}|${fromLabel.end}` : '');
    setPurposeId('');
    setTitle('');
    setDescription('');
    setFormError(null);
    setDone(false);
  }, [open, initialDate, initialSlotLabel, room?.id]);

  const purposesQuery = useQuery({
    queryKey: ['event-purposes'],
    queryFn: () => purposesApi.list(),
    enabled: open,
  });

  const occupancyQuery = useQuery({
    queryKey: ['room-occupancy', room?.id, date],
    queryFn: () => roomsApi.occupancy(room!.id, date),
    enabled: open && Boolean(room && date) && !isMoscowSunday(date),
  });

  const sunday = Boolean(date && isMoscowSunday(date));

  const freeSlots = useMemo(() => {
    if (!date || sunday || !occupancyQuery.data) return [];
    return freeRuzSlots(date, occupancyQuery.data);
  }, [date, sunday, occupancyQuery.data]);

  // Drop prefilled slot if it becomes occupied after occupancy loads.
  useEffect(() => {
    if (!slotKey || !occupancyQuery.isSuccess) return;
    const stillFree = freeSlots.some((s) => `${s.start}|${s.end}` === slotKey);
    if (!stillFree) setSlotKey('');
  }, [slotKey, freeSlots, occupancyQuery.isSuccess]);

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!room) throw new Error('Аудитория не выбрана');
      if (!date) throw new Error('Укажите дату');
      if (isMoscowSunday(date)) throw new Error(SUNDAY_BOOKING_HINT);
      const [start, end] = slotKey.split('|');
      if (!start || !end) throw new Error('Выберите время (пару)');
      if (purposeId === '') throw new Error('Выберите цель мероприятия');
      const trimmed = title.trim();
      if (!trimmed || trimmed.length > 200) {
        throw new Error('Название: от 1 до 200 символов');
      }

      const draft = await bookingsApi.create({
        room_id: Number(room.id),
        purpose_id: purposeId,
        title: trimmed,
        description: description.trim() || undefined,
        starts_at: moscowDateTimeToUtcIso(date, start),
        ends_at: moscowDateTimeToUtcIso(date, end),
        action: 'CREATE',
      });
      return bookingsApi.submit(draft.id);
    },
    onSuccess: () => {
      setDone(true);
      qc.invalidateQueries({ queryKey: ['my-bookings'] });
      qc.invalidateQueries({ queryKey: ['bookings'] });
      qc.invalidateQueries({ queryKey: ['room-occupancy', room?.id] });
      qc.invalidateQueries({ queryKey: ['rooms'] });
    },
    onError: (err) => {
      setFormError(bookingErrorRu(getErrorDetail(err)));
    },
  });

  const handleSubmit = () => {
    setFormError(null);
    createMutation.mutate();
  };

  const busy = createMutation.isPending;
  const canSubmit =
    Boolean(room && date && !sunday && slotKey && purposeId !== '' && title.trim()) && !busy;

  return (
    <Dialog open={open} onClose={busy ? undefined : onClose} fullWidth maxWidth="sm">
      <DialogTitle>
        {done ? 'Заявка отправлена' : `Бронирование — ауд. ${room?.number ?? ''}`}
      </DialogTitle>
      <DialogContent dividers>
        {done ? (
          <Stack spacing={1.5}>
            <Alert severity="success">
              Заявка отправлена на модерацию. Статус можно проверить в личном кабинете.
            </Alert>
            <Typography variant="body2" color="text.secondary">
              Корпус: {room?.building}. Дата: {date}.
              {slotKey ? ` Время: ${slotKey.replace('|', ' — ')}.` : ''}
            </Typography>
            <Button component={RouterLink} to="/account" variant="outlined" size="small">
              Открыть личный кабинет
            </Button>
          </Stack>
        ) : (
          <Stack spacing={2} sx={{ pt: 1 }}>
            {room && (
              <Typography variant="body2" color="text.secondary">
                {room.building}, вместимость {room.capacity}
              </Typography>
            )}

            <TextField
              type="date"
              label="Дата"
              InputLabelProps={{ shrink: true }}
              value={date}
              onChange={(e) => {
                setDate(e.target.value);
                setSlotKey('');
              }}
              required
              fullWidth
            />

            {sunday && (
              <Alert severity="warning">{SUNDAY_BOOKING_HINT}</Alert>
            )}

            <FormControl fullWidth required disabled={!date || sunday || occupancyQuery.isLoading}>
              <InputLabel id="book-slot-label">Время (пара)</InputLabel>
              <Select
                labelId="book-slot-label"
                label="Время (пара)"
                value={slotKey || 'none'}
                onChange={(e) =>
                  setSlotKey(e.target.value === 'none' ? '' : e.target.value)
                }
              >
                <MenuItem value="none" disabled>
                  {!date
                    ? 'Сначала выберите дату'
                    : sunday
                      ? 'В воскресенье слотов нет'
                    : occupancyQuery.isLoading
                      ? 'Загрузка свободных слотов…'
                      : freeSlots.length === 0
                        ? 'Нет свободных пар'
                        : 'Выберите пару'}
                </MenuItem>
                {freeSlots.map((s) => (
                  <MenuItem key={s.label} value={`${s.start}|${s.end}`}>
                    {s.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {date && !sunday && occupancyQuery.isError && (
              <Alert severity="warning">Не удалось загрузить занятость аудитории.</Alert>
            )}

            <FormControl fullWidth required>
              <InputLabel id="book-purpose-label">Цель</InputLabel>
              <Select
                labelId="book-purpose-label"
                label="Цель"
                value={purposeId === '' ? '' : String(purposeId)}
                onChange={(e) =>
                  setPurposeId(e.target.value === '' ? '' : Number(e.target.value))
                }
              >
                {(purposesQuery.data ?? []).map((p) => (
                  <MenuItem key={p.id} value={String(p.id)}>
                    {p.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {purposesQuery.isError && (
              <Alert severity="warning">Не удалось загрузить список целей.</Alert>
            )}

            <TextField
              label="Название мероприятия"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              fullWidth
              inputProps={{ maxLength: 200 }}
              helperText={`${title.trim().length}/200`}
            />

            <TextField
              label="Описание (необязательно)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              fullWidth
              multiline
              minRows={2}
            />

            {(formError || createMutation.isError) && (
              <Alert severity="error">{formError ?? 'Не удалось отправить заявку.'}</Alert>
            )}

            <Box>
              <Typography variant="caption" color="text.secondary">
                Заявка сразу уйдёт на модерацию (как в Telegram-боте).
              </Typography>
            </Box>
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        {done ? (
          <Button onClick={onClose}>Закрыть</Button>
        ) : (
          <>
            <Button onClick={onClose} disabled={busy}>
              Отмена
            </Button>
            <Button variant="contained" onClick={handleSubmit} disabled={!canSubmit}>
              {busy ? 'Отправка…' : 'Отправить на модерацию'}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
}
