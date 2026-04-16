import { alpha, createTheme } from '@mui/material/styles';

const primary = '#095ab4';
const primaryDark = '#00458f';
const primarySoft = '#d7e3ff';
const secondary = '#4b5f83';
const tertiary = '#815100';
const success = '#3f8f57';
const warning = '#c67f00';
const error = '#ba1a1a';
const surface = '#f9f9ff';
const surfaceLow = '#f2f3fb';
const surfaceHigh = '#e7e8f0';
const surfacePaper = '#ffffff';
const outline = '#c2c6d4';
const textPrimary = '#191c21';
const textSecondary = '#4f5f77';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: primary,
      dark: primaryDark,
      light: '#3573cf',
      contrastText: '#ffffff',
    },
    secondary: {
      main: secondary,
      dark: '#34476a',
      light: '#c1d5ff',
      contrastText: '#ffffff',
    },
    success: {
      main: success,
      light: '#eaf6ec',
      dark: '#24683a',
      contrastText: '#ffffff',
    },
    warning: {
      main: warning,
      light: '#fff3db',
      dark: '#8a5900',
      contrastText: '#ffffff',
    },
    error: {
      main: error,
      light: '#ffdad6',
      dark: '#93000a',
      contrastText: '#ffffff',
    },
    info: {
      main: '#3f78c5',
      light: '#edf4ff',
      dark: '#17437f',
      contrastText: '#ffffff',
    },
    background: {
      default: surface,
      paper: surfacePaper,
    },
    text: {
      primary: textPrimary,
      secondary: textSecondary,
    },
    divider: alpha(outline, 0.45),
    ledger: {
      ink: '#0a2546',
      surface,
      surfaceLow,
      surfaceHigh,
      surfacePaper,
      outline,
      primarySoft,
      tertiarySoft: '#ffddb7',
    },
  },
  typography: {
    fontFamily: '"Inter", "Segoe UI", sans-serif',
    h1: {
      fontFamily: '"Manrope", "Inter", sans-serif',
      fontWeight: 800,
      letterSpacing: '-0.05em',
      lineHeight: 0.94,
    },
    h2: {
      fontFamily: '"Manrope", "Inter", sans-serif',
      fontWeight: 800,
      letterSpacing: '-0.04em',
      lineHeight: 0.98,
    },
    h3: {
      fontFamily: '"Manrope", "Inter", sans-serif',
      fontWeight: 800,
      letterSpacing: '-0.03em',
    },
    h4: {
      fontFamily: '"Manrope", "Inter", sans-serif',
      fontWeight: 700,
      letterSpacing: '-0.025em',
    },
    h5: {
      fontFamily: '"Manrope", "Inter", sans-serif',
      fontWeight: 700,
      letterSpacing: '-0.02em',
    },
    h6: {
      fontFamily: '"Manrope", "Inter", sans-serif',
      fontWeight: 700,
      letterSpacing: '-0.015em',
    },
    subtitle1: {
      fontWeight: 600,
      letterSpacing: '-0.01em',
    },
    subtitle2: {
      fontWeight: 700,
      letterSpacing: '0.02em',
    },
    body1: {
      lineHeight: 1.7,
    },
    body2: {
      lineHeight: 1.6,
    },
    button: {
      fontFamily: '"Manrope", "Inter", sans-serif',
      fontWeight: 700,
      textTransform: 'none',
      letterSpacing: '0.01em',
    },
    overline: {
      fontWeight: 800,
      letterSpacing: '0.18em',
      textTransform: 'uppercase',
    },
    caption: {
      letterSpacing: '0.03em',
    },
  },
  shape: {
    borderRadius: 14,
  },
  shadows: Array(25).fill('none'),
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        ':root': {
          '--ledger-primary': primary,
          '--ledger-primary-dark': primaryDark,
          '--ledger-secondary': secondary,
          '--ledger-tertiary': tertiary,
          '--ledger-surface': surface,
          '--ledger-surface-low': surfaceLow,
          '--ledger-surface-high': surfaceHigh,
          '--ledger-paper': surfacePaper,
          '--ledger-outline': outline,
          '--ledger-ink': '#0a2546',
          '--ledger-gradient': 'linear-gradient(135deg, #000666 0%, #1a237e 100%)',
        },
        body: {
          color: textPrimary,
          backgroundColor: surface,
        },
      },
    },
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
      styleOverrides: {
        root: {
          borderRadius: 14,
          padding: '11px 20px',
          boxShadow: 'none',
        },
        contained: {
          background: 'var(--ledger-gradient)',
          color: '#ffffff',
          '&:hover': {
            background: 'linear-gradient(135deg, #001466 0%, #111d6b 100%)',
            boxShadow: 'none',
          },
        },
        outlined: {
          borderColor: alpha(outline, 0.55),
          backgroundColor: alpha(surfacePaper, 0.85),
          '&:hover': {
            borderColor: alpha(primary, 0.35),
            backgroundColor: alpha(surfaceLow, 0.8),
          },
        },
        text: {
          '&:hover': {
            backgroundColor: alpha(primary, 0.06),
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          boxShadow: 'none',
        },
        rounded: {
          borderRadius: 18,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          boxShadow: 'none',
          borderRadius: 18,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 14,
            backgroundColor: surfacePaper,
            '& fieldset': {
              borderColor: alpha(outline, 0.45),
            },
            '&:hover fieldset': {
              borderColor: alpha(primary, 0.35),
            },
            '&.Mui-focused fieldset': {
              borderColor: primary,
              borderWidth: 1.5,
            },
          },
          '& .MuiInputLabel-root.Mui-focused': {
            color: primary,
          },
          '& .MuiFormHelperText-root': {
            marginLeft: 2,
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          fontWeight: 700,
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 16,
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: `1px solid ${alpha(outline, 0.22)}`,
          paddingTop: 18,
          paddingBottom: 18,
        },
        head: {
          backgroundColor: surfaceLow,
          color: textSecondary,
          fontWeight: 800,
          fontSize: '0.72rem',
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          borderBottom: `1px solid ${alpha(outline, 0.18)}`,
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          height: 6,
          borderRadius: 999,
          backgroundColor: alpha('#64779d', 0.14),
        },
        bar: {
          borderRadius: 999,
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundImage: 'none',
          backgroundColor: '#f8f9fd',
        },
      },
    },
  },
});

export default theme;
