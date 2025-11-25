/**
 * Landing/Home page
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { Container, Typography, Button, Box, Paper, Grid } from '@mui/material';
import { Description, CheckCircle, CloudUpload } from '@mui/icons-material';

export default function Home() {
  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 8, mb: 4, textAlign: 'center' }}>
        <Description sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />
        <Typography variant="h2" component="h1" gutterBottom fontWeight="bold">
          RFP Document Compliance Checker
        </Typography>
        <Typography variant="h5" color="text.secondary" paragraph>
          Automatically analyze RFP requirements and match them with your submitted documents
        </Typography>
        <Box sx={{ mt: 4 }}>
          <Button
            component={Link}
            to="/login"
            variant="contained"
            size="large"
            sx={{ mr: 2, px: 4, py: 1.5 }}
          >
            Get Started
          </Button>
          <Button
            component={Link}
            to="/register"
            variant="outlined"
            size="large"
            sx={{ px: 4, py: 1.5 }}
          >
            Sign Up
          </Button>
        </Box>
      </Box>

      <Grid container spacing={4} sx={{ mt: 6 }}>
        <Grid item xs={12} md={4}>
          <Paper elevation={2} sx={{ p: 3, textAlign: 'center', height: '100%' }}>
            <CloudUpload sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Upload Documents
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Upload your RFP document and supporting files in various formats (PDF, Word, etc.)
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper elevation={2} sx={{ p: 3, textAlign: 'center', height: '100%' }}>
            <Description sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              AI-Powered Analysis
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Our LLM extracts requirements and matches them with your documents using advanced NLP
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper elevation={2} sx={{ p: 3, textAlign: 'center', height: '100%' }}>
            <CheckCircle sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Instant Results
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Get a detailed compliance report showing which documents are present, missing, or need review
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      <Box sx={{ mt: 8, mb: 4, textAlign: 'center' }}>
        <Typography variant="h4" gutterBottom>
          Supported Formats
        </Typography>
        <Typography variant="body1" color="text.secondary">
          PDF • Word (DOCX/DOC) • Text Files • Markdown • RTF • ODT
        </Typography>
      </Box>
    </Container>
  );
}
