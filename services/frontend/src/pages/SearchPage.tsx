import { useMemo, useState } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';
import {
  Box, Paper, Typography, Stack, TextField, FormControlLabel, Checkbox,
  Button, Grid, Card, CardContent, CardActions, Chip, Alert, CircularProgress,
  FormControl, InputLabel, Select, MenuItem,
} from '@mui/material';
import { buildingsApi, roomsApi } from '../api/endpoints';
import type { Room, RoomSearchFilters } from '../types';
import { freeRuzSlotLabels, RUZ_TIME_SLOTS } from '../utils/dateTime';

function RoomCard({
  room,
  date,
  highlightSlot,
}: {
  room: Room;
  date?: string;
  highlightSlot?: string;
}) {
  const occupancyQuery = useQuery({
    queryKey: ['room-occupancy', room.id, date],
    queryFn: () => roomsApi.occupancy(room.id, date!),
    enabled: Boolean(date),
  });

  const freeSlots = useMemo(() => {
    if (!date || !occupancyQuery.data) return [];
    return freeRuzSlotLabels(date, occupancyQuery.data);
  }, [date, occupancyQuery.data]);

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Typography variant="h6">Ауд. {room.number}</Typography>
        <Typography variant="body2" color="text.secondary">
          Корпус: {room.building}
        </Typography>
        <Typography variant="body2" sx={{ mt: 1 }}>
          Вместимость: {room.capacity}
        </Typography>
        <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap', gap: 0.5 }}>
          {room.hasProjector && <Chip size="small" label="Проектор" />}
          {room.hasWhiteboard && <Chip size="small" label="Доска" />}
        </Stack>

        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
            Свободное время
          </Typography>
          {!date && (
            <Typography variant="caption" color="text.secondary">
              Укажите дату в фильтрах, чтобы увидеть слоты
            </Typography>
          )}
          {date && occupancyQuery.isLoading && (
            <Typography variant="caption" color="text.secondary">
              Загрузка слотов…
            </Typography>
          )}
          {date && occupancyQuery.isError && (
            <Typography variant="caption" color="error">
              Не удалось загрузить занятость
            </Typography>
          )}
          {date && occupancyQuery.isSuccess && freeSlots.length === 0 && (
            <Typography variant="caption" color="text.secondary">
              На этот день свободных пар нет
            </Typography>
          )}
          {date && occupancyQuery.isSuccess && freeSlots.length > 0 && (
            <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
              {freeSlots.map((label) => (
                <Chip
                  key={label}
                  size="small"
                  variant={highlightSlot === label ? 'filled' : 'outlined'}
                  color={highlightSlot === label ? 'success' : 'default'}
                  label={label}
                />
              ))}
            </Stack>
          )}
        </Box>
      </CardContent>
      <CardActions>
        <Button size="small" variant="outlined" disabled>
          Забронировать
        </Button>
      </CardActions>
    </Card>
  );
}

export default function SearchPage() {
  const [filters, setFilters] = useState<RoomSearchFilters>({});
  const [active, setActive] = useState<RoomSearchFilters>({});
  const [slotError, setSlotError] = useState<string | null>(null);

  const buildingsQuery = useQuery({
    queryKey: ['buildings'],
    queryFn: () => buildingsApi.list(),
  });

  const { data: rooms, isFetching, isError } = useQuery({
    queryKey: ['rooms', active],
    queryFn: () => roomsApi.search(active),
  });

  // Prefetch occupancy for visible rooms when a date is selected (cards also query).
  useQueries({
    queries: (rooms ?? []).map((room) => ({
      queryKey: ['room-occupancy', room.id, active.date],
      queryFn: () => roomsApi.occupancy(room.id, active.date!),
      enabled: Boolean(active.date && rooms?.length),
    })),
  });

  const selectedPair = useMemo(() => {
    if (!filters.fromTime || !filters.toTime) return 'any';
    const found = RUZ_TIME_SLOTS.find(
      (s) => s.start === filters.fromTime && s.end === filters.toTime,
    );
    return found ? `${found.start}|${found.end}` : 'custom';
  }, [filters.fromTime, filters.toTime]);

  const highlightSlot = useMemo(() => {
    if (!active.fromTime || !active.toTime) return undefined;
    return RUZ_TIME_SLOTS.find((s) => s.start === active.fromTime && s.end === active.toTime)
      ?.label;
  }, [active.fromTime, active.toTime]);

  const handleSearch = () => {
    const hasTime = Boolean(filters.fromTime || filters.toTime);
    const hasFullSlot = Boolean(filters.date && filters.fromTime && filters.toTime);

    if (hasTime && !hasFullSlot) {
      setSlotError('Чтобы искать свободные аудитории, укажите и дату, и время.');
      return;
    }
    if (hasFullSlot && filters.fromTime! >= filters.toTime!) {
      setSlotError('Время окончания должно быть позже начала.');
      return;
    }
    setSlotError(null);
    setActive({
      ...filters,
      ...(hasFullSlot ? {} : { fromTime: undefined, toTime: undefined }),
    });
  };

  const usingAvailability = Boolean(active.date && active.fromTime && active.toTime);

  return (
    <Box>
      <Typography variant="h1" sx={{ fontSize: '1.75rem', mb: 2 }}>
        Поиск аудиторий
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack spacing={2}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} flexWrap="wrap">
            <FormControl sx={{ minWidth: 220 }}>
              <InputLabel id="building-label">Корпус</InputLabel>
              <Select
                labelId="building-label"
                label="Корпус"
                value={filters.building ?? 'any'}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    building: e.target.value === 'any' ? undefined : e.target.value,
                  })
                }
              >
                <MenuItem value="any">Любой</MenuItem>
                {(buildingsQuery.data ?? []).map((b) => (
                  <MenuItem key={b.code} value={b.code}>
                    {b.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              type="number"
              label="Мин. вместимость"
              value={filters.minCapacity ?? ''}
              onChange={(e) =>
                setFilters({ ...filters, minCapacity: e.target.value ? +e.target.value : undefined })
              }
              inputProps={{ min: 1 }}
              sx={{ minWidth: 180 }}
            />
            <TextField
              type="date"
              label="Дата"
              InputLabelProps={{ shrink: true }}
              value={filters.date ?? ''}
              onChange={(e) => setFilters({ ...filters, date: e.target.value || undefined })}
              sx={{ minWidth: 180 }}
            />
            <FormControl sx={{ minWidth: 220 }}>
              <InputLabel id="pair-label">Время</InputLabel>
              <Select
                labelId="pair-label"
                label="Время"
                value={selectedPair === 'custom' ? 'any' : selectedPair}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v === 'any') {
                    setFilters({ ...filters, fromTime: undefined, toTime: undefined });
                    return;
                  }
                  const [start, end] = v.split('|');
                  setFilters({ ...filters, fromTime: start, toTime: end });
                }}
              >
                <MenuItem value="any">Не важно</MenuItem>
                {RUZ_TIME_SLOTS.map((s) => (
                  <MenuItem key={s.label} value={`${s.start}|${s.end}`}>
                    {s.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
          <Stack direction="row" spacing={3} alignItems="center" flexWrap="wrap">
            <FormControlLabel
              control={
                <Checkbox
                  checked={!!filters.hasProjector}
                  onChange={(e) =>
                    setFilters({ ...filters, hasProjector: e.target.checked || undefined })
                  }
                />
              }
              label="Проектор"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={!!filters.hasWhiteboard}
                  onChange={(e) =>
                    setFilters({ ...filters, hasWhiteboard: e.target.checked || undefined })
                  }
                />
              }
              label="Доска"
            />
            <Box sx={{ flexGrow: 1 }} />
            <Button variant="contained" onClick={handleSearch} disabled={isFetching}>
              Найти
            </Button>
          </Stack>
          {slotError && <Alert severity="warning">{slotError}</Alert>}
          <Typography variant="caption" color="text.secondary">
            Укажите дату и нажмите «Найти», чтобы на карточках появились свободные пары.
            Дата + время — только аудитории, свободные в этот интервал.
          </Typography>
        </Stack>
      </Paper>

      {buildingsQuery.isError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Не удалось загрузить список корпусов.
        </Alert>
      )}

      {isError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Не удалось получить список аудиторий. Проверьте вход и что backend запущен.
        </Alert>
      )}

      {usingAvailability && !isFetching && !isError && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Показаны свободные аудитории на {active.date}, {active.fromTime}–{active.toTime} (МСК).
        </Alert>
      )}

      {isFetching && (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress />
        </Box>
      )}

      {!isFetching && !isError && (
        <Grid container spacing={2}>
          {(rooms ?? []).map((room) => (
            <Grid item xs={12} sm={6} md={4} key={room.id}>
              <RoomCard room={room} date={active.date} highlightSlot={highlightSlot} />
            </Grid>
          ))}
          {(rooms?.length ?? 0) === 0 && (
            <Grid item xs={12}>
              <Alert severity="info">По заданным параметрам аудитории не найдены.</Alert>
            </Grid>
          )}
        </Grid>
      )}
    </Box>
  );
}
