/**
 * Landing/Home page
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { Container, Typography, Button, Box, Paper, Grid, Fade, Grow } from '@mui/material';
import { Description, CheckCircle, CloudUpload, TrendingUp, Speed, Security } from '@mui/icons-material';

export default function Home() {
  return (
    <Box sx={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      {/* Hero Section */}
      <Container maxWidth="lg" sx={{ pt: 5, pb: 8 }}>
        <Fade in timeout={1000}>
          <Box textAlign="center" mb={8}>
            <Box
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 1,
                bgcolor: 'rgba(255, 255, 255, 0.2)',
                borderRadius: 10,
                px: 3,
                py: 1,
                mb: 3,
                backdropFilter: 'blur(10px)',
              }}
            >
              <TrendingUp sx={{ color: 'white' }} />
              <Typography variant="body2" sx={{ color: 'white', fontWeight: 600 }}>
                AI-Powered Compliance Analysis
              </Typography>
            </Box>

            <Typography
              variant="h1"
              sx={{
                fontSize: { xs: '2.5rem', md: '4rem' },
                fontWeight: 900,
                color: 'white',
                mb: 3,
                lineHeight: 1.2,
                textShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
              }}
            >
              Eval RFP
            </Typography>

            <Typography
              variant="h5"
              sx={{
                color: 'rgba(255, 255, 255, 0.9)',
                mb: 5,
                maxWidth: 600,
                mx: 'auto',
                fontWeight: 400,
              }}
            >
              Automatically analyze RFP requirements and match them with your submitted documents using advanced AI
            </Typography>

            <Box display="flex" gap={2} justifyContent="center" flexWrap="wrap">
              <Button
                component={Link}
                to="/login"
                variant="contained"
                size="large"
                sx={{
                  bgcolor: 'white',
                  color: '#667eea',
                  px: 5,
                  py: 2,
                  fontSize: '1.1rem',
                  borderRadius: 3,
                  boxShadow: '0 8px 30px rgba(0, 0, 0, 0.3)',
                  '&:hover': {
                    bgcolor: 'white',
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 40px rgba(0, 0, 0, 0.4)',
                  },
                }}
              >
                Get Started
              </Button>
              <Button
                component={Link}
                to="/register"
                variant="outlined"
                size="large"
                sx={{
                  borderColor: 'white',
                  color: 'white',
                  borderWidth: 2,
                  px: 5,
                  py: 2,
                  fontSize: '1.1rem',
                  borderRadius: 3,
                  '&:hover': {
                    borderWidth: 2,
                    borderColor: 'white',
                    bgcolor: 'rgba(255, 255, 255, 0.1)',
                    transform: 'translateY(-4px)',
                  },
                }}
              >
                Sign Up
              </Button>
            </Box>
          </Box>
        </Fade>

        {/* Features Grid */}
        <Grid container spacing={4} sx={{ mt: 4 }}>
          {[
            {
              icon: <CloudUpload sx={{ fontSize: 50 }} />,
              title: 'Upload Documents',
              description: 'Upload your RFP document and supporting files in various formats (PDF, Word, etc.)',
              delay: 200,
            },
            {
              icon: <Speed sx={{ fontSize: 50 }} />,
              title: 'AI-Powered Analysis',
              description: 'Our LLM extracts requirements and matches them with your documents using advanced NLP',
              delay: 400,
            },
            {
              icon: <CheckCircle sx={{ fontSize: 50 }} />,
              title: 'Instant Results',
              description: 'Get a detailed compliance report showing which documents are present, missing, or need review',
              delay: 600,
            },
          ].map((feature, index) => (
            <Grid item xs={12} md={4} key={index}>
              <Grow in timeout={1000 + feature.delay}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 4,
                    height: '100%',
                    textAlign: 'center',
                    borderRadius: 4,
                    background: 'rgba(255, 255, 255, 0.95)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(255, 255, 255, 0.3)',
                    transition: 'all 0.3s',
                    '&:hover': {
                      transform: 'translateY(-10px)',
                      boxShadow: '0 20px 40px rgba(0, 0, 0, 0.2)',
                    },
                  }}
                >
                  <Box
                    sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 90,
                      height: 90,
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      color: 'white',
                      mb: 3,
                      boxShadow: '0 8px 24px rgba(102, 126, 234, 0.4)',
                    }}
                  >
                    {feature.icon}
                  </Box>
                  <Typography variant="h5" fontWeight={700} gutterBottom>
                    {feature.title}
                  </Typography>
                  <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.8 }}>
                    {feature.description}
                  </Typography>
                </Paper>
              </Grow>
            </Grid>
          ))}
        </Grid>

        {/* Supported Formats */}
        <Fade in timeout={2000}>
          <Box
            sx={{
              mt: 10,
              p: 4,
              borderRadius: 4,
              background: 'rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              textAlign: 'center',
            }}
          >
            <Typography variant="h6" sx={{ color: 'white', mb: 2, fontWeight: 700 }}>
              Supported Formats
            </Typography>
            <Typography variant="body1" sx={{ color: 'rgba(255, 255, 255, 0.9)', fontSize: '1.1rem' }}>
              PDF • Word (DOCX/DOC) • Text Files • Markdown • RTF • ODT
            </Typography>
          </Box>
        </Fade>
      </Container>
    </Box>
  );
}
