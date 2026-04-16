import React from 'react';
import { Link } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Grid,
  Stack,
  Typography,
} from '@mui/material';
import {
  AutoAwesome,
  CheckCircleOutline,
  CloudUploadOutlined,
  SecurityOutlined,
  TrendingUp,
  ViewListOutlined,
} from '@mui/icons-material';

const features = [
  {
    icon: <CloudUploadOutlined sx={{ fontSize: 34 }} />,
    title: 'Upload RFPs and supporting files',
    description:
      'Bring your solicitation package and evidence pool into one workspace without changing the current backend flow.',
  },
  {
    icon: <AutoAwesome sx={{ fontSize: 34 }} />,
    title: 'AI-assisted compliance review',
    description:
      'Analyze requirements, compare them with your submitted documents, and keep the results grounded in the existing API responses.',
  },
  {
    icon: <ViewListOutlined sx={{ fontSize: 34 }} />,
    title: 'Editorial audit trail',
    description:
      'Review completion status, missing evidence, and analysis history through a cleaner command-center experience.',
  },
];

export default function Home() {
  return (
    <Box sx={{ minHeight: '100vh', overflow: 'hidden' }}>
      <Box
        sx={{
          position: 'relative',
          background: 'var(--ledger-gradient)',
          color: '#fff',
          pb: { xs: 8, md: 12 },
        }}
      >
        <Box
          className="ledger-mesh"
          sx={{ position: 'absolute', inset: 0, opacity: 0.3 }}
        />
        <Container sx={{ position: 'relative', zIndex: 1, py: { xs: 4, md: 6 } }}>
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            spacing={2}
            sx={{ mb: { xs: 6, md: 10 } }}
          >
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: 2.5,
                  bgcolor: 'rgba(255,255,255,0.12)',
                  display: 'grid',
                  placeItems: 'center',
                  fontFamily: '"Manrope", sans-serif',
                  fontWeight: 800,
                }}
              >
                ER
              </Box>
              <Typography variant="h6" sx={{ color: '#fff' }}>
                EvalRFP
              </Typography>
            </Stack>

            <Stack direction="row" spacing={1.5}>
              <Button component={Link} to="/login" variant="text" sx={{ color: '#fff' }}>
                Login
              </Button>
              <Button
                component={Link}
                to="/register"
                variant="outlined"
                sx={{
                  color: '#fff',
                  borderColor: 'rgba(255,255,255,0.3)',
                  bgcolor: 'rgba(255,255,255,0.06)',
                }}
              >
                Create account
              </Button>
            </Stack>
          </Stack>

          <Grid container spacing={5} alignItems="center">
            <Grid item xs={12} lg={7}>
              <Typography variant="overline" sx={{ color: 'rgba(255,255,255,0.72)' }}>
                The Intelligent Ledger
              </Typography>
              <Typography
                variant="h1"
                sx={{
                  color: '#fff',
                  fontSize: { xs: '3.2rem', md: '5.2rem' },
                  mb: 3,
                  maxWidth: 760,
                }}
              >
                Verified intelligence for high-stakes RFP compliance.
              </Typography>
              <Typography
                sx={{
                  color: 'rgba(255,255,255,0.82)',
                  fontSize: { xs: '1.05rem', md: '1.2rem' },
                  maxWidth: 640,
                  mb: 4,
                }}
              >
                A redesigned workspace for procurement teams to upload evidence, run
                analyses, and inspect requirement-level results while staying connected to
                the backend already powering your project.
              </Typography>

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} mb={4}>
                <Button
                  component={Link}
                  to="/login"
                  variant="contained"
                  size="large"
                  sx={{ bgcolor: '#fff', color: 'primary.main', '&:hover': { bgcolor: '#eef4ff' } }}
                >
                  Enter Workspace
                </Button>
                <Button
                  component={Link}
                  to="/register"
                  variant="outlined"
                  size="large"
                  sx={{ color: '#fff', borderColor: 'rgba(255,255,255,0.28)' }}
                >
                  Start with your team
                </Button>
              </Stack>

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <CheckCircleOutline />
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.84)' }}>
                    Compliance-ready outputs
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={1} alignItems="center">
                  <SecurityOutlined />
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.84)' }}>
                    Secure auth integration
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={1} alignItems="center">
                  <TrendingUp />
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.84)' }}>
                    Faster evidence reviews
                  </Typography>
                </Stack>
              </Stack>
            </Grid>

            <Grid item xs={12} lg={5}>
              <Box
                className="ledger-glass ledger-float"
                sx={{
                  borderRadius: 6,
                  p: 3,
                  border: '1px solid rgba(255,255,255,0.16)',
                }}
              >
                <Typography variant="overline" sx={{ color: 'rgba(255,255,255,0.72)' }}>
                  Workspace Preview
                </Typography>
                <Box
                  sx={{
                    mt: 2,
                    borderRadius: 4,
                    bgcolor: 'rgba(255,255,255,0.08)',
                    p: 3,
                  }}
                >
                  <Typography variant="h5" sx={{ color: '#fff', mb: 1 }}>
                    Intelligence Verification
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.72)', mb: 3 }}>
                    Review upload readiness, completion signals, and analysis history in a
                    cleaner command-center layout.
                  </Typography>
                  <Stack spacing={2}>
                    {[
                      ['Active analyses', 'Workspace history'],
                      ['Evidence coverage', 'Live upload queue'],
                      ['Requirement details', 'Exportable results'],
                    ].map(([title, subtitle]) => (
                      <Box
                        key={title}
                        sx={{
                          borderRadius: 3,
                          p: 2,
                          bgcolor: 'rgba(255,255,255,0.08)',
                          border: '1px solid rgba(255,255,255,0.1)',
                        }}
                      >
                        <Typography variant="subtitle1" sx={{ color: '#fff' }}>
                          {title}
                        </Typography>
                        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                          {subtitle}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Box>
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      <Container sx={{ py: { xs: 6, md: 10 } }}>
        <Box sx={{ mb: 5 }}>
          <Typography variant="overline" color="text.secondary">
            Workflow
          </Typography>
          <Typography variant="h3" sx={{ color: '#0a2546', mt: 1, mb: 1 }}>
            A redesigned frontend around your existing analysis engine
          </Typography>
          <Typography color="text.secondary" sx={{ maxWidth: 720 }}>
            The UI can change without disturbing your route structure, auth context, or API
            contracts. These screens stay focused on orchestration, review, and auditability.
          </Typography>
        </Box>

        <Grid container spacing={3}>
          {features.map((feature) => (
            <Grid item xs={12} md={4} key={feature.title}>
              <Card
                sx={{
                  height: '100%',
                  bgcolor: 'rgba(255,255,255,0.85)',
                  border: '1px solid rgba(194, 198, 212, 0.3)',
                }}
              >
                <CardContent sx={{ p: 4 }}>
                  <Box
                    sx={{
                      width: 60,
                      height: 60,
                      borderRadius: 3,
                      display: 'grid',
                      placeItems: 'center',
                      mb: 3,
                      color: 'primary.main',
                      bgcolor: 'rgba(9, 90, 180, 0.08)',
                    }}
                  >
                    {feature.icon}
                  </Box>
                  <Typography variant="h5" sx={{ color: '#0a2546', mb: 1.5 }}>
                    {feature.title}
                  </Typography>
                  <Typography color="text.secondary">{feature.description}</Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
}
