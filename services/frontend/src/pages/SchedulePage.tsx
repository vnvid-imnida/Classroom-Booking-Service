import { useState } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { useQuery } from '@tanstack/react-query';
import {
  Box, Paper, Typography, Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Stack, Chip, Alert,
} from '@mui/material';
import { bookingsApi } from '../api/endpoints';
import type { Booking } from '../types';
import { STATUS_LABELS, STATUS_COLORS } from '../types';

export default function SchedulePage() {
  const [selected, setSelected] = useState<Booking | null>(null);

  const { data: bookings, isLoading, isError } = useQuery<Booking[]>({
    queryKey: ['bookings'],
    queryFn: () => bookingsApi.list(),
  });

  const events = (bookings ?? []).map((b) => ({
    id: b.id,
    title: `${b.roomNumber ? `[${b.roomNumber}] ` : ''}${b.title}`,
    start: b.start,
    end: b.end,
    extendedProps: { booking: b },
    backgroundColor: STATUS_COLORS[b.status],
    borderColor: STATUS_COLORS[b.status],
  }));

  return (
    <Box>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
        <Typography variant="h1" sx={{ fontSize: '1.75rem' }}>Расписание</Typography>
        <Stack direction="row" spacing={1}>
          <Chip label={STATUS_LABELS.approved} sx={{ bgcolor: STATUS_COLORS.approved, color: 'white' }} size="small" />
          <Chip label={STATUS_LABELS.pending}  sx={{ bgcolor: STATUS_COLORS.pending,  color: 'white' }} size="small" />
          <Chip label={STATUS_LABELS.rejected} sx={{ bgcolor: STATUS_COLORS.rejected, color: 'white' }} size="small" />
        </Stack>
      </Stack>

      {isError && <Alert severity="warning" sx={{ mb: 2 }}>
        Не удалось загрузить бронирования. Календарь показан без данных.
      </Alert>}

      <Paper sx={{ p: 2 }}>
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          locale="ru"
          firstDay={1}
          height="auto"
          slotMinTime="08:00:00"
          slotMaxTime="22:00:00"
          allDaySlot={false}
          weekends
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay',
          }}
          buttonText={{
            today: 'Сегодня', month: 'Месяц', week: 'Неделя', day: 'День',
          }}
          events={events}
          eventClick={(info) => {
            const booking = info.event.extendedProps.booking as Booking | undefined;
            if (booking) setSelected(booking);
          }}
        />
        {isLoading && <Typography sx={{ mt: 1 }} variant="body2">Загрузка...</Typography>}
      </Paper>

      <Dialog open={!!selected} onClose={() => setSelected(null)} fullWidth maxWidth="sm">
        <DialogTitle>{selected?.title}</DialogTitle>
        <DialogContent dividers>
          {selected && (
            <Stack spacing={1}>
              <Typography variant="body2">
                <strong>Аудитория:</strong> {selected.roomNumber ?? selected.roomId}
              </Typography>
              <Typography variant="body2">
                <strong>Начало:</strong> {new Date(selected.start).toLocaleString('ru-RU')}
              </Typography>
              <Typography variant="body2">
                <strong>Конец:</strong> {new Date(selected.end).toLocaleString('ru-RU')}
              </Typography>
              <Box>
                <strong>Статус: </strong>
                <Chip
                  size="small"
                  label={STATUS_LABELS[selected.status]}
                  sx={{ bgcolor: STATUS_COLORS[selected.status], color: 'white', ml: 0.5 }}
                />
              </Box>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelected(null)}>Закрыть</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
