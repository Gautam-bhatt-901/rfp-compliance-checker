import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  AppBar,
  Avatar,
  Box,
  Button,
  IconButton,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  AddCircleOutline,
  HelpOutline,
  Menu,
  NotificationsNone,
} from '@mui/icons-material';
import { useAuth } from '../../context/AuthContext';

export default function Navbar({ onMenuClick }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const activeLabel = location.pathname.startsWith('/analysis/')
    ? 'Compliance'
    : location.pathname === '/analyze'
    ? 'RFPs'
    : 'Dashboard';

  return (
    <AppBar
      position="sticky"
      color="transparent"
      elevation={0}
      sx={{
        borderBottom: '1px solid rgba(194, 198, 212, 0.45)',
        bgcolor: 'rgba(249, 249, 255, 0.86)',
        backdropFilter: 'blur(18px)',
      }}
    >
      <Toolbar sx={{ minHeight: 76, px: { xs: 2, md: 3 } }}>
        <Stack direction="row" alignItems="center" spacing={1.5} sx={{ minWidth: 0 }}>
          <IconButton
            onClick={onMenuClick}
            sx={{ display: { lg: 'none' }, color: 'text.primary' }}
          >
            <Menu />
          </IconButton>
          <Box
            onClick={() => navigate('/dashboard')}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              cursor: 'pointer',
            }}
          >
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: 2.5,
                background: 'var(--ledger-gradient)',
                color: '#fff',
                display: 'grid',
                placeItems: 'center',
                fontFamily: '"Manrope", sans-serif',
                fontWeight: 800,
                letterSpacing: '-0.04em',
              }}
            >
              ER
            </Box>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="h6" sx={{ color: '#0a2546' }}>
                EvalRFP
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {activeLabel}
              </Typography>
            </Box>
          </Box>
        </Stack>

        <Box sx={{ flexGrow: 1 }} />

        <Stack
          direction="row"
          alignItems="center"
          spacing={{ xs: 0.5, md: 1 }}
          sx={{ minWidth: 0 }}
        >
          <Tooltip title="Help">
            <IconButton sx={{ color: 'text.secondary', display: { xs: 'none', sm: 'inline-flex' } }}>
              <HelpOutline />
            </IconButton>
          </Tooltip>
          <Tooltip title="Notifications">
            <IconButton sx={{ color: 'text.secondary', display: { xs: 'none', sm: 'inline-flex' } }}>
              <NotificationsNone />
            </IconButton>
          </Tooltip>
          <Button
            startIcon={<AddCircleOutline />}
            onClick={() => navigate('/analyze')}
            variant="contained"
            sx={{
              display: { xs: 'none', md: 'inline-flex' },
              minWidth: 0,
            }}
          >
            New Analysis
          </Button>
          <Stack
            direction="row"
            alignItems="center"
            spacing={1.5}
            sx={{
              pl: { xs: 0.5, md: 2 },
              ml: { xs: 0.5, md: 1 },
              borderLeft: '1px solid rgba(194, 198, 212, 0.45)',
              minWidth: 0,
            }}
          >
            <Avatar
              sx={{
                width: 40,
                height: 40,
                bgcolor: 'primary.main',
                fontWeight: 800,
              }}
            >
              {(user?.email || 'E')[0].toUpperCase()}
            </Avatar>
            <Box sx={{ display: { xs: 'none', sm: 'block' }, minWidth: 0 }}>
              <Typography variant="subtitle2" noWrap sx={{ color: '#0a2546' }}>
                {user?.full_name || 'Workspace User'}
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap>
                {user?.email}
              </Typography>
            </Box>
          </Stack>
        </Stack>
      </Toolbar>
    </AppBar>
  );
}
