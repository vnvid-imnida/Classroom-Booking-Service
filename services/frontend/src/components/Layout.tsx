import { AppBar, Toolbar, Typography, Button, Container, Box, Stack } from '@mui/material';
import { Link as RouterLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { isAdminRole, ROLE_LABELS } from '../types';

const baseNav = [
  { to: '/schedule', label: 'Расписание' },
  { to: '/search',   label: 'Поиск аудиторий' },
  { to: '/account',  label: 'Личный кабинет' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = isAdminRole(user?.role)
    ? [...baseNav, { to: '/admin', label: 'Админ-панель' }]
    : baseNav;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static" color="primary">
        <Toolbar>
          <Typography variant="h6" component={RouterLink} to="/schedule"
            sx={{ color: 'inherit', textDecoration: 'none', flexShrink: 0, mr: 4 }}>
            СПбПУ · Бронирование
          </Typography>
          <Stack direction="row" spacing={1} sx={{ flexGrow: 1 }}>
            {navItems.map((item) => (
              <Button
                key={item.to}
                component={RouterLink}
                to={item.to}
                color="inherit"
                sx={{
                  fontWeight: location.pathname.startsWith(item.to) ? 700 : 400,
                  textTransform: 'none',
                }}
              >
                {item.label}
              </Button>
            ))}
          </Stack>
          {user && (
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography variant="body2">
                {user.fullName || user.email}
                {user.role && (
                  <> · {ROLE_LABELS[user.role] ?? user.role}</>
                )}
              </Typography>
              <Button color="inherit" variant="outlined" onClick={logout} sx={{ textTransform: 'none' }}>
                Выйти
              </Button>
            </Stack>
          )}
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ flexGrow: 1, py: 3 }}>
        <Outlet />
      </Container>
      <Box component="footer" sx={{ py: 2, textAlign: 'center', color: 'text.secondary' }}>
        <Typography variant="caption">© СПбПУ — Система бронирования аудиторий</Typography>
      </Box>
    </Box>
  );
}
