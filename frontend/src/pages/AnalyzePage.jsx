/**
 * Analysis page - Upload and analyze RFP
 * MIGRATED FROM: Original DashboardPage.jsx
 * PRESERVED: All core functionality
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Alert,
  LinearProgress,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  CloudUpload,
  Description,
  CheckCircle,
  InsertDriveFile,
} from '@mui/icons-material';
import { rfpAPI } from '../services/api';
import Navbar from '../components/Layout/Navbar';

export default function AnalyzePage() {
  const navigate = useNavigate();
  const [rfpFile, setRfpFile] = useState(null);
  const [providedFiles, setProvidedFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  const handleRfpUpload = (e) => {
    setRfpFile(e.target.files[0]);
    setResults(null);
    setError('');
  };

  const handleProvidedFilesUpload = (e) => {
    setProvidedFiles(Array.from(e.target.files));
    setResults(null);
    setError('');
  };

  const handleAnalyze = async () => {
    if (!rfpFile || providedFiles.length === 0) {
      setError('Please upload both RFP document and provided documents');
      return;
    }

    setLoading(true);
    setError('');
    setProgress(0);

    try {
      const data = await rfpAPI.analyzeCompliance(rfpFile, providedFiles, setProgress);
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed. Please try again.');
    } finally {
      setLoading(false);
      setProgress(0);
    }
  };

  const getStatusColor = (status) => {
    if (status.includes('Present')) return 'success';
    if (status.includes('Missing')) return 'error';
    return 'warning';
  };

  const downloadCSV = () => {
    if (!results) return;
    
    const headers = ['Required Document', 'Status', 'Matched File'];
    const rows = results.matches.map(m => [
      m.required_document,
      m.status,
      m.matched_file
    ]);
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'rfp_compliance_results.csv';
    a.click();
  };

  return (
    <>
      <Navbar />
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
            🔍 New RFP Analysis
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Upload your RFP document and supporting files to check compliance
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {/* Upload Section */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={6}>
            <Paper 
              elevation={0} 
              sx={{ 
                p: 4, 
                border: '2px dashed',
                borderColor: rfpFile ? 'success.main' : 'divider',
                bgcolor: rfpFile ? 'success.light' : 'background.paper',
                transition: 'all 0.3s',
              }}
            >
              <Box sx={{ textAlign: 'center' }}>
                <Description sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom fontWeight="bold">
                  1️⃣ Upload RFP Document
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  PDF, Word, Text, Markdown, RTF, or ODT
                </Typography>
                <Button
                  variant="contained"
                  component="label"
                  startIcon={<CloudUpload />}
                  size="large"
                >
                  Choose RFP File
                  <input
                    type="file"
                    hidden
                    accept=".pdf,.docx,.doc,.txt,.md,.rtf,.odt"
                    onChange={handleRfpUpload}
                  />
                </Button>
                {rfpFile && (
                  <Alert severity="success" sx={{ mt: 3 }}>
                    <strong>✓ Loaded:</strong> {rfpFile.name}
                  </Alert>
                )}
              </Box>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper 
              elevation={0} 
              sx={{ 
                p: 4, 
                border: '2px dashed',
                borderColor: providedFiles.length > 0 ? 'success.main' : 'divider',
                bgcolor: providedFiles.length > 0 ? 'success.light' : 'background.paper',
                transition: 'all 0.3s',
              }}
            >
              <Box sx={{ textAlign: 'center' }}>
                <InsertDriveFile sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom fontWeight="bold">
                  2️⃣ Upload Your Documents
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Select multiple files to check against RFP
                </Typography>
                <Button
                  variant="contained"
                  component="label"
                  startIcon={<CloudUpload />}
                  size="large"
                >
                  Choose Documents
                  <input
                    type="file"
                    hidden
                    multiple
                    accept=".pdf,.docx,.doc,.txt,.md,.rtf,.odt"
                    onChange={handleProvidedFilesUpload}
                  />
                </Button>
                {providedFiles.length > 0 && (
                  <Alert severity="success" sx={{ mt: 3 }}>
                    <strong>✓ Loaded:</strong> {providedFiles.length} document(s)
                    <List dense>
                      {providedFiles.slice(0, 3).map((file, idx) => (
                        <ListItem key={idx}>
                          <ListItemIcon>
                            <CheckCircle fontSize="small" color="success" />
                          </ListItemIcon>
                          <ListItemText primary={file.name} />
                        </ListItem>
                      ))}
                      {providedFiles.length > 3 && (
                        <ListItem>
                          <ListItemText 
                            primary={`... and ${providedFiles.length - 3} more`}
                            sx={{ fontStyle: 'italic' }}
                          />
                        </ListItem>
                      )}
                    </List>
                  </Alert>
                )}
              </Box>
            </Paper>
          </Grid>
        </Grid>

        {/* Analyze Button */}
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Button
            variant="contained"
            size="large"
            onClick={handleAnalyze}
            disabled={!rfpFile || providedFiles.length === 0 || loading}
            sx={{ 
              px: 6, 
              py: 2,
              fontSize: '1.1rem',
              boxShadow: 3,
            }}
          >
            {loading ? 'Analyzing...' : '🔍 Analyze Compliance'}
          </Button>
        </Box>

        {loading && (
          <Box sx={{ mb: 4 }}>
            <LinearProgress variant="determinate" value={progress} sx={{ height: 8, borderRadius: 1 }} />
            <Typography variant="body2" textAlign="center" sx={{ mt: 1 }} color="text.secondary">
              Processing documents... {progress}%
            </Typography>
          </Box>
        )}

        {/* Results Section */}
        {results && (
          <Box>
            <Typography variant="h5" fontWeight="bold" gutterBottom>
              📊 Compliance Results
            </Typography>

            {/* Stats Cards */}
            <Grid container spacing={2} sx={{ mb: 4 }}>
              <Grid item xs={6} sm={3}>
                <Card>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="h4" fontWeight="bold">{results.total}</Typography>
                    <Typography variant="body2" color="text.secondary">Total Required</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Card sx={{ bgcolor: 'success.light' }}>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="h4" fontWeight="bold">{results.present}</Typography>
                    <Typography variant="body2">✅ Present</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Card sx={{ bgcolor: 'warning.light' }}>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="h4" fontWeight="bold">{results.review}</Typography>
                    <Typography variant="body2">⚠️ Review</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Card sx={{ bgcolor: 'error.light' }}>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="h4" fontWeight="bold">{results.missing}</Typography>
                    <Typography variant="body2">❌ Missing</Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {/* Completion Rate */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="body1" gutterBottom>
                <strong>Completion Rate:</strong> {results.completion_rate.toFixed(1)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={results.completion_rate}
                sx={{ height: 12, borderRadius: 1 }}
                color={results.completion_rate >= 80 ? 'success' : results.completion_rate >= 60 ? 'warning' : 'error'}
              />
            </Box>

            {/* Results Table */}
            <TableContainer component={Paper} sx={{ mb: 3 }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Required Document</strong></TableCell>
                    <TableCell align="center"><strong>Status</strong></TableCell>
                    <TableCell><strong>Matched File</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {results.matches.map((match, index) => (
                    <TableRow key={index} hover>
                      <TableCell>{match.required_document}</TableCell>
                      <TableCell align="center">
                        <Chip
                          label={match.status}
                          color={getStatusColor(match.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{match.matched_file}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Button variant="contained" onClick={downloadCSV}>
                📥 Download CSV
              </Button>
              <Button
                variant="outlined"
                onClick={() => {
                  setResults(null);
                  setRfpFile(null);
                  setProvidedFiles([]);
                }}
              >
                🔄 New Analysis
              </Button>
              <Button
                variant="outlined"
                onClick={() => navigate('/dashboard')}
              >
                📊 View Dashboard
              </Button>
            </Box>

            {results.extraction_cost > 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 3, textAlign: 'center' }}>
                💰 API Cost: ${results.extraction_cost.toFixed(4)}
              </Typography>
            )}
          </Box>
        )}
      </Container>
    </>
  );
}
