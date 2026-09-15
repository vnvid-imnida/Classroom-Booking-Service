import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box, Paper, Typography, Stack, TextField, FormControlLabel, Checkbox,
  Button, Grid, Card, CardContent, CardActions, Chip, Alert, CircularProgress,
  FormControl, InputLabel, Select, MenuItem,
} from '@mui/material';
import { buildingsApi, roomsApi } from '../api/endpoints';
import type { RoomSearchFilters } from '../types';

export default function SearchPage() {
  const [filters, setFilters] = useState<RoomSearchFilters>({});
  const [active, setActive] = useState<RoomSearchFilters>({});

  const buildingsQuery = useQuery({
    queryKey: ['buildings'],
    queryFn: () => buildingsApi.list(),
  });

  const { data: rooms, isFetching, isError } = useQuery({
    queryKey: ['rooms', active],
    queryFn: () => roomsApi.search(active),
  });

  const handleSearch = () => setActive({ ...filters });

  return (
    <Box>
      <Typography variant="h1" sx={{ fontSize: '1.75rem', mb: 2 }}>
        Поиск аудиторий
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack spacing={2}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
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
              helperText="Фильтр по слоту — на следующем шаге"
            />
            <TextField
              type="time"
              label="С"
              InputLabelProps={{ shrink: true }}
              value={filters.fromTime ?? ''}
              onChange={(e) => setFilters({ ...filters, fromTime: e.target.value || undefined })}
            />
            <TextField
              type="time"
              label="До"
              InputLabelProps={{ shrink: true }}
              value={filters.toTime ?? ''}
              onChange={(e) => setFilters({ ...filters, toTime: e.target.value || undefined })}
            />
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

      {isFetching && (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress />
        </Box>
      )}

      {!isFetching && !isError && (
        <Grid container spacing={2}>
          {(rooms ?? []).map((room) => (
            <Grid item xs={12} sm={6} md={4} key={room.id}>
              <Card>
                <CardContent>
                  <Typography variant="h6">Ауд. {room.number}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Корпус: {room.building}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Вместимость: {room.capacity}
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap' }}>
                    {room.hasProjector && <Chip size="small" label="Проектор" />}
                    {room.hasWhiteboard && <Chip size="small" label="Доска" />}
                  </Stack>
                </CardContent>
                <CardActions>
                  <Button size="small" variant="outlined" disabled>
                    Забронировать
                  </Button>
                </CardActions>
              </Card>
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
