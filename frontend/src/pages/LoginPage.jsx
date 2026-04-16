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
  Visibility,
  VisibilityOff,
} from '@mui/icons-material';
import AuthShell from '../components/Layout/AuthShell';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Enterprise Login"
      subtitle="Access your intelligence ledger, active analysis queue, and compliance audit history."
      footer={
        <Box mt={3} textAlign="center">
          <Typography variant="body2" color="text.secondary">
            New to EvalRFP?{' '}
            <Box
              component={Link}
              to="/register"
              sx={{
                fontWeight: 700,
                color: 'primary.main',
                textDecoration: 'none',
              }}
            >
              Create an account
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
            label="Secure Password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
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

          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={loading}
            endIcon={<ArrowForward />}
            sx={{ py: 1.8 }}
          >
            {loading ? 'Signing in...' : 'Sign in to Workspace'}
          </Button>

          <Typography variant="body2" color="text.secondary" textAlign="center">
            Your session uses the same secure backend authentication flow already configured for this app.
          </Typography>
        </Stack>
      </Box>
    </AuthShell>
  );
}
