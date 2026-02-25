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
  Fade,
} from '@mui/material';
import {
  Description,
  Dashboard,
  CloudUpload,
  AccountCircle,
  Logout,
  TrendingUp,
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
    return null;
  }

  return (
    <AppBar 
      position="sticky" 
      elevation={0}
      sx={{
        background: 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(99, 102, 241, 0.1)',
        boxShadow: '0 4px 30px rgba(0, 0, 0, 0.05)',
      }}
    >
      <Container maxWidth="xl">
        <Toolbar sx={{ justifyContent: 'space-between', py: 1 }}>
          {/* Logo */}
          <Box
            display="flex"
            alignItems="center"
            sx={{ cursor: 'pointer' }}
            onClick={() => navigate('/dashboard')}
          >
            <Box
              sx={{
                background: 'linear-gradient(135deg, #6366f1 0%, #ec4899 100%)',
                borderRadius: '12px',
                p: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mr: 2,
                boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'scale(1.05) rotate(5deg)',
                },
              }}
            >
              <TrendingUp sx={{ color: 'white', fontSize: 28 }} />
            </Box>
            <Typography
              variant="h6"
              sx={{
                background: 'linear-gradient(135deg, #6366f1 0%, #ec4899 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                fontWeight: 800,
                letterSpacing: '-0.5px',
              }}
            >
              Eval RFP
            </Typography>
          </Box>

          {/* Navigation Items */}
          <Box display="flex" alignItems="center" gap={1}>
            <Button
              startIcon={<Dashboard />}
              onClick={() => navigate('/dashboard')}
              sx={{
                color: isActive('/dashboard') ? 'primary.main' : 'text.secondary',
                bgcolor: isActive('/dashboard') ? 'primary.light' : 'transparent',
                px: 3,
                py: 1,
                borderRadius: 2.5,
                fontWeight: 600,
                transition: 'all 0.3s',
                '&:hover': {
                  bgcolor: isActive('/dashboard') ? 'primary.light' : 'action.hover',
                  transform: 'translateY(-2px)',
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
                px: 3,
                py: 1,
                borderRadius: 2.5,
                fontWeight: 600,
                transition: 'all 0.3s',
                '&:hover': {
                  bgcolor: isActive('/analyze') ? 'primary.light' : 'action.hover',
                  transform: 'translateY(-2px)',
                },
              }}
            >
              New Analysis
            </Button>

            {/* User Menu */}
            <Box
              sx={{
                ml: 2,
                pl: 2,
                borderLeft: '2px solid',
                borderColor: 'divider',
              }}
            >
              <IconButton
                onClick={handleMenu}
                sx={{
                  p: 0,
                  transition: 'transform 0.2s',
                  '&:hover': {
                    transform: 'scale(1.1)',
                  },
                }}
              >
                <Avatar
                  sx={{
                    bgcolor: 'primary.main',
                    background: 'linear-gradient(135deg, #6366f1 0%, #ec4899 100%)',
                    width: 40,
                    height: 40,
                    fontWeight: 700,
                    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                  }}
                >
                  {user.email[0].toUpperCase()}
                </Avatar>
              </IconButton>
              <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleClose}
                TransitionComponent={Fade}
                PaperProps={{
                  sx: {
                    mt: 1.5,
                    borderRadius: 3,
                    minWidth: 200,
                    boxShadow: '0 10px 40px rgba(0, 0, 0, 0.1)',
                  },
                }}
              >
                <MenuItem disabled sx={{ opacity: 1, '&.Mui-disabled': { opacity: 1 } }}>
                  <Box>
                    <Typography variant="subtitle2" fontWeight={700} color="text.primary">
                      {user.full_name || 'My Account'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {user.email}
                    </Typography>
                  </Box>
                </MenuItem>
                <MenuItem
                  onClick={handleLogout}
                  sx={{
                    color: 'error.main',
                    mt: 1,
                    borderRadius: 1.5,
                    mx: 1,
                    '&:hover': {
                      bgcolor: 'error.light',
                      color: 'error.dark',
                    },
                  }}
                >
                  <Logout sx={{ mr: 1, fontSize: 20 }} />
                  Logout
                </MenuItem>
              </Menu>
            </Box>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
}
