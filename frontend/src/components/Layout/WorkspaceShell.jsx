import React, { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Typography,
} from '@mui/material';
import {
  AddCircleOutline,
  DashboardCustomize,
  DescriptionOutlined,
  ExitToApp,
  FactCheckOutlined,
  Inventory2Outlined,
} from '@mui/icons-material';
import { useAuth } from '../../context/AuthContext';
import Navbar from './Navbar';

const drawerWidth = 280;

function SidebarContent({ onNavigate }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();

  const items = useMemo(
    () => [
      {
        label: 'Command Center',
        caption: 'Dashboard',
        icon: <DashboardCustomize fontSize="small" />,
        path: '/dashboard',
        active:
          location.pathname === '/dashboard' || location.pathname.startsWith('/analysis/'),
      },
      {
        label: 'RFP Workspace',
        caption: 'Analyze',
        icon: <DescriptionOutlined fontSize="small" />,
        path: '/analyze',
        active: location.pathname === '/analyze',
      },
      {
        label: 'Audit Ledger',
        caption: 'History',
        icon: <FactCheckOutlined fontSize="small" />,
        path: '/dashboard',
        active: false,
      },
      {
        label: 'Evidence Pool',
        caption: 'Library',
        icon: <Inventory2Outlined fontSize="small" />,
        path: '/analyze',
        active: false,
      },
    ],
    [location.pathname]
  );

  const handleNavigate = (path) => {
    navigate(path);
    onNavigate?.();
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
    onNavigate?.();
  };

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: '#f8f9fd',
      }}
    >
      <Box sx={{ px: 3, pt: 3, pb: 4 }}>
        <Stack direction="row" spacing={1.5} alignItems="center" mb={2}>
          <Box
            sx={{
              width: 44,
              height: 44,
              borderRadius: 3,
              background: 'var(--ledger-gradient)',
              display: 'grid',
              placeItems: 'center',
              color: '#fff',
              fontFamily: '"Manrope", sans-serif',
              fontWeight: 800,
            }}
          >
            ER
          </Box>
          <Box>
            <Typography variant="h6" sx={{ color: '#0a2546' }}>
              The Intelligent Ledger
            </Typography>
            <Typography variant="overline" color="text.secondary">
              AI Verification Suite
            </Typography>
          </Box>
        </Stack>
        <Button
          fullWidth
          variant="contained"
          startIcon={<AddCircleOutline />}
          onClick={() => handleNavigate('/analyze')}
          sx={{ justifyContent: 'flex-start', py: 1.4 }}
        >
          Upload Document
        </Button>
      </Box>

      <Stack spacing={1} sx={{ px: 2, flexGrow: 1 }}>
        {items.map((item) => (
          <Button
            key={item.label}
            onClick={() => handleNavigate(item.path)}
            startIcon={item.icon}
            sx={{
              justifyContent: 'flex-start',
              px: 2,
              py: 1.5,
              borderRadius: 3,
              color: item.active ? 'primary.dark' : 'text.secondary',
              bgcolor: item.active ? 'rgba(9, 90, 180, 0.09)' : 'transparent',
              borderLeft: item.active ? '3px solid #095ab4' : '3px solid transparent',
            }}
          >
            <Box sx={{ textAlign: 'left' }}>
              <Typography variant="subtitle2" sx={{ fontFamily: '"Inter", sans-serif' }}>
                {item.label}
              </Typography>
              <Typography variant="caption" color="inherit" sx={{ opacity: 0.8 }}>
                {item.caption}
              </Typography>
            </Box>
          </Button>
        ))}
      </Stack>

      <Box sx={{ px: 3, py: 3 }}>
        <Divider sx={{ mb: 2 }} />
        <Button
          fullWidth
          variant="text"
          startIcon={<ExitToApp />}
          onClick={handleLogout}
          sx={{ justifyContent: 'flex-start', color: 'text.secondary' }}
        >
          Logout
        </Button>
      </Box>
    </Box>
  );
}

export default function WorkspaceShell({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggleMobile = () => {
    setMobileOpen((prev) => !prev);
  };

  const closeMobile = () => {
    setMobileOpen(false);
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', bgcolor: 'background.default' }}>
      <Box
        component="nav"
        sx={{
          width: { lg: drawerWidth },
          flexShrink: { lg: 0 },
        }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={closeMobile}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', lg: 'none' },
            '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box' },
          }}
        >
          <SidebarContent onNavigate={closeMobile} />
        </Drawer>
        <Drawer
          variant="permanent"
          open
          sx={{
            display: { xs: 'none', lg: 'block' },
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box',
              borderRight: '1px solid rgba(194, 198, 212, 0.45)',
            },
          }}
        >
          <SidebarContent />
        </Drawer>
      </Box>

      <Box sx={{ flexGrow: 1, minWidth: 0 }} className="ledger-shell-bg">
        <Navbar onMenuClick={toggleMobile} />
        <Box
          component="main"
          sx={{
            px: { xs: 2, md: 4, xl: 6 },
            py: { xs: 3, md: 4, xl: 5 },
            maxWidth: 1500,
            width: '100%',
            mx: 'auto',
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
}
