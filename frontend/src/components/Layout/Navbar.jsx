/**
 * Navigation bar component
 */
import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Container,
} from '@mui/material';
import {
  Description,
  Dashboard,
  CloudUpload,
  AccountCircle,
  Logout,
} from '@mui/icons-material';
import { useAuth } from '../../context/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [anchorEl, setAnchorEl] = useState(null);

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
    handleClose();
  };

  const isActive = (path) => location.pathname === path;

  if (!user) {
    return null; // Don't show navbar if not logged in
  }

  return (
    <AppBar 
      position="sticky" 
      elevation={0}
      sx={{ 
        bgcolor: 'background.paper',
        borderBottom: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Container maxWidth="xl">
        <Toolbar disableGutters>
          {/* Logo */}
          <Description sx={{ mr: 1, color: 'primary.main' }} />
          <Typography
            variant="h6"
            noWrap
            component="div"
            sx={{
              mr: 4,
              fontWeight: 700,
              color: 'text.primary',
              cursor: 'pointer',
            }}
            onClick={() => navigate('/dashboard')}
          >
            RFP Pre Evaluator
          </Typography>

          {/* Navigation Items */}
          <Box sx={{ flexGrow: 1, display: 'flex', gap: 1 }}>
            <Button
              startIcon={<Dashboard />}
              onClick={() => navigate('/dashboard')}
              sx={{
                color: isActive('/dashboard') ? 'primary.main' : 'text.secondary',
                bgcolor: isActive('/dashboard') ? 'primary.light' : 'transparent',
                '&:hover': {
                  bgcolor: isActive('/dashboard') ? 'primary.light' : 'action.hover',
                },
              }}
            >
              Dashboard
            </Button>
            <Button
              startIcon={<CloudUpload />}
              onClick={() => navigate('/analyze')}
              sx={{
                color: isActive('/analyze') ? 'primary.main' : 'text.secondary',
                bgcolor: isActive('/analyze') ? 'primary.light' : 'transparent',
                '&:hover': {
                  bgcolor: isActive('/analyze') ? 'primary.light' : 'action.hover',
                },
              }}
            >
              New Analysis
            </Button>
          </Box>

          {/* User Menu */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" color="text.secondary">
              {user.email}
            </Typography>
            <IconButton onClick={handleMenu} size="small">
              <Avatar sx={{ bgcolor: 'primary.main', width: 36, height: 36 }}>
                {user.email[0].toUpperCase()}
              </Avatar>
            </IconButton>
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleClose}
              transformOrigin={{ horizontal: 'right', vertical: 'top' }}
              anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
            >
              <MenuItem disabled>
                <AccountCircle sx={{ mr: 1 }} />
                {user.full_name || 'My Account'}
              </MenuItem>
              <MenuItem onClick={handleLogout}>
                <Logout sx={{ mr: 1 }} />
                Logout
              </MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
}
