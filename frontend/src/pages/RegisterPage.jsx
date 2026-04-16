import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  IconButton,
  InputAdornment,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import {
  AlternateEmail,
  ArrowForward,
  Lock,
  PersonOutline,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material';
import AuthShell from '../components/Layout/AuthShell';
import { useAuth } from '../context/AuthContext';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);
    try {
      await register(email, password, fullName);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Create Workspace Access"
      subtitle="Set up your account to start submitting RFPs, organizing evidence, and reviewing compliance results."
      footer={
        <Box mt={3} textAlign="center">
          <Typography variant="body2" color="text.secondary">
            Already registered?{' '}
            <Box
              component={Link}
              to="/login"
              sx={{ fontWeight: 700, color: 'primary.main', textDecoration: 'none' }}
            >
              Sign in here
            </Box>
          </Typography>
        </Box>
      }
    >
      <Box
        component="form"
        onSubmit={handleSubmit}
        sx={{
          p: { xs: 3, sm: 4 },
          borderRadius: 5,
          bgcolor: 'rgba(255,255,255,0.92)',
          border: '1px solid rgba(194, 198, 212, 0.35)',
          boxShadow: '0 24px 60px rgba(10, 37, 70, 0.08)',
        }}
      >
        <Stack spacing={3}>
          {error && (
            <Alert severity="error" onClose={() => setError('')}>
              {error}
            </Alert>
          )}

          <TextField
            fullWidth
            label="Full Name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <PersonOutline color="action" />
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            label="Work Email Address"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <AlternateEmail color="action" />
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            label="Password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            helperText="Minimum 6 characters"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Lock color="action" />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowPassword((value) => !value)} edge="end">
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            label="Confirm Password"
            type={showConfirmPassword ? 'text' : 'password'}
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Lock color="action" />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowConfirmPassword((value) => !value)} edge="end">
                    {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={loading}
            endIcon={<ArrowForward />}
            sx={{ py: 1.8 }}
          >
            {loading ? 'Creating account...' : 'Create Workspace'}
          </Button>
        </Stack>
      </Box>
    </AuthShell>
  );
}
