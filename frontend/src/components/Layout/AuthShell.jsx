import React from 'react';
import { Box, Container, Stack, Typography } from '@mui/material';
import { AutoAwesome, Security, VerifiedUser } from '@mui/icons-material';

export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: '1.2fr 1fr' },
        backgroundColor: 'background.default',
      }}
    >
      <Box
        sx={{
          display: { xs: 'none', md: 'flex' },
          position: 'relative',
          overflow: 'hidden',
          px: { md: 8, lg: 12 },
          py: 10,
          color: '#fff',
          background: 'var(--ledger-gradient)',
        }}
      >
        <Box
          className="ledger-mesh"
          sx={{
            position: 'absolute',
            inset: 0,
            opacity: 0.35,
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            right: '-12%',
            bottom: '-10%',
            width: 360,
            height: 360,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.08)',
            filter: 'blur(6px)',
          }}
        />
        <Stack spacing={4} justifyContent="center" sx={{ position: 'relative', zIndex: 1, maxWidth: 560 }}>
          <Box>
            <Typography variant="overline" sx={{ color: 'rgba(255,255,255,0.72)' }}>
              Verified Intelligence
            </Typography>
            <Typography variant="h1" sx={{ fontSize: { md: '4.2rem', lg: '5.2rem' }, color: '#fff', mb: 3 }}>
              Enterprise-grade AI verification for modern RFPs.
            </Typography>
            <Typography sx={{ color: 'rgba(255,255,255,0.82)', fontSize: '1.1rem', maxWidth: 460 }}>
              The intelligent ledger for procurement teams that need a clear audit trail,
              credible evidence tracking, and faster compliance reviews.
            </Typography>
          </Box>

          <Box
            className="ledger-glass"
            sx={{
              borderRadius: 4,
              p: 3,
              border: '1px solid rgba(255,255,255,0.14)',
            }}
          >
            <Stack direction="row" spacing={2} alignItems="center">
              <Box
                sx={{
                  width: 52,
                  height: 52,
                  borderRadius: 3,
                  display: 'grid',
                  placeItems: 'center',
                  bgcolor: 'rgba(255,255,255,0.12)',
                }}
              >
                <AutoAwesome />
              </Box>
              <Box>
                <Typography variant="overline" sx={{ color: 'rgba(255,255,255,0.74)' }}>
                  AI-Powered Automation
                </Typography>
                <Typography variant="subtitle1" sx={{ color: '#fff' }}>
                  Intelligent document matching with audit-friendly outputs
                </Typography>
              </Box>
            </Stack>
          </Box>
        </Stack>
      </Box>

      <Container maxWidth="sm" sx={{ display: 'flex', alignItems: 'center', py: { xs: 4, md: 8 } }}>
        <Box sx={{ width: '100%' }}>
          <Box sx={{ mb: 4 }}>
            <Typography variant="h3" sx={{ color: '#0a2546', mb: 1 }}>
              {title}
            </Typography>
            <Typography color="text.secondary">{subtitle}</Typography>
          </Box>
          {children}
          {footer}
          <Stack
            direction="row"
            spacing={3}
            justifyContent="center"
            sx={{ mt: 4, color: 'text.secondary', flexWrap: 'wrap' }}
          >
            <Stack direction="row" spacing={1} alignItems="center">
              <VerifiedUser fontSize="small" />
              <Typography variant="caption">SOC2 aligned</Typography>
            </Stack>
            <Stack direction="row" spacing={1} alignItems="center">
              <Security fontSize="small" />
              <Typography variant="caption">Secure workspace</Typography>
            </Stack>
          </Stack>
        </Box>
      </Container>
    </Box>
  );
}
