import { createTheme } from '@mui/material/styles';
import { ruRU as coreRu } from '@mui/material/locale';

export const theme = createTheme(
  {
    palette: {
      mode: 'light',
      primary: { main: '#0F4C81' },
      secondary: { main: '#FFB400' },
      background: { default: '#F5F7FA' },
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
      h1: { fontSize: '2rem', fontWeight: 700 },
      h2: { fontSize: '1.5rem', fontWeight: 600 },
    },
    shape: { borderRadius: 10 },
    components: {
      MuiButton: { defaultProps: { disableElevation: true } },
    },
  },
  coreRu,
);
