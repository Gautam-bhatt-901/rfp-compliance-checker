/**
 * Analysis page - Upload and analyze MULTIPLE RFPs
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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
} from '@mui/material';
import {
  CloudUpload,
  Description,
  CheckCircle,
  InsertDriveFile,
  ExpandMore,
  ExpandLess,
  FolderOpen,
} from '@mui/icons-material';
import { rfpAPI } from '../services/api';
import Navbar from '../components/Layout/Navbar';

export default function AnalyzePage() {
  const navigate = useNavigate();
  
  const [rfpFiles, setRfpFiles] = useState([]);
  const [providedFiles, setProvidedFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [expandedDescriptions, setExpandedDescriptions] = useState({});
  
  // Toggle description expand/collapse
  const toggleDescription = (rfpIndex, matchIndex) => {
    const key = `${rfpIndex}-${matchIndex}`;
    setExpandedDescriptions(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  // CHANGED: results now contains batch data
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  // UPDATED: Handle multiple RFP files
  const handleRfpUpload = (e) => {
    setRfpFiles(Array.from(e.target.files));
    setResults(null);
    setError('');
  };

  const handleProvidedFilesUpload = (e) => {
    setProvidedFiles(Array.from(e.target.files));
    setResults(null);
    setError('');
  };

  const handleAnalyze = async () => {
    if (rfpFiles.length === 0 || providedFiles.length === 0) {
      setError('Please upload both RFP document(s) and supporting documents');
      return;
    }

    setLoading(true);
    setError('');
    setProgress(0);

    try {
      // CHANGED: Pass rfpFiles array instead of single file
      const data = await rfpAPI.analyzeCompliance(rfpFiles, providedFiles, setProgress);
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

  // UPDATED: Download CSV for all RFPs
  const downloadCSV = () => {
  if (!results || !results.rfp_results) return;
  
  let csv = "RFP Filename,Required Document,Description,Status,Matched File\n";
  
  results.rfp_results.forEach(rfpResult => {
    rfpResult.matches.forEach(match => {
      const description = (match.description || "").replace(/"/g, '""'); // Escape quotes
      csv += `"${rfpResult.rfp_filename}","${match.required_document}","${description}","${match.status}","${match.matched_file}"\n`;
    });
  });
  
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `batch_analysis_${results.batch_id}.csv`;
  a.click();
  };

  // UPDATED: Download CSV for single RFP
  const downloadSingleRfpCSV = (rfpResult) => {
  const headers = ["Required Document", "Description", "Status", "Matched File"];
  const rows = rfpResult.matches.map(m => {
    const description = (m.description || "").replace(/"/g, '""'); // Escape quotes
    return [`"${m.required_document}"`, `"${description}"`, `"${m.status}"`, `"${m.matched_file}"`];
  });
  
  const csv = [headers.map(h => `"${h}"`).join(","), ...rows.map(row => row.join(","))].join("\n");
  
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${rfpResult.rfp_filename.replace('.pdf', '')}_results.csv`;
  a.click();
  };

  return (
    <>
      <Navbar />
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            🔍 New RFP Analysis
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Upload multiple RFP documents and supporting files to check compliance
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" onClose={() => setError('')} sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Upload Section */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {/* UPDATED: Multiple RFP Files Upload */}
          <Grid item xs={12} md={6}>
            <Paper
              elevation={3}
              sx={{
                p: 4,
                textAlign: 'center',
                borderRadius: 2,
                border: 2,
                borderColor: rfpFiles.length > 0 ? 'success.main' : 'divider',
                bgcolor: rfpFiles.length > 0 ? 'success.light' : 'background.paper',
                transition: 'all 0.3s',
              }}
            >
              <Description sx={{ fontSize: 60, mb: 2, color: 'primary.main' }} />
              <Typography variant="h6" gutterBottom>
                1️⃣ Upload RFP Documents
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Select one or more RFP files (PDF, Word, Text, etc.)
              </Typography>

              <Button
                variant="contained"
                component="label"
                startIcon={<CloudUpload />}
                size="large"
              >
                Choose RFP Files
                <input
                  type="file"
                  hidden
                  multiple
                  accept=".pdf,.docx,.doc,.txt,.md,.rtf,.odt"
                  onChange={handleRfpUpload}
                />
              </Button>

              {rfpFiles.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="success.main" gutterBottom>
                    ✓ Loaded: {rfpFiles.length} RFP document(s)
                  </Typography>
                  <List dense>
                    {rfpFiles.map((file, idx) => (
                      <ListItem key={idx}>
                        <ListItemIcon>
                          <Description fontSize="small" />
                        </ListItemIcon>
                        <ListItemText 
                          primary={file.name}
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Paper>
          </Grid>

          {/* Supporting Documents Upload (unchanged) */}
          <Grid item xs={12} md={6}>
            <Paper
              elevation={3}
              sx={{
                p: 4,
                textAlign: 'center',
                borderRadius: 2,
                border: 2,
                borderColor: providedFiles.length > 0 ? 'success.main' : 'divider',
                bgcolor: providedFiles.length > 0 ? 'success.light' : 'background.paper',
                transition: 'all 0.3s',
              }}
            >
              <FolderOpen sx={{ fontSize: 60, mb: 2, color: 'primary.main' }} />
              <Typography variant="h6" gutterBottom>
                2️⃣ Upload Supporting Documents
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Select multiple files to check against ALL RFPs
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
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="success.main" gutterBottom>
                    ✓ Loaded: {providedFiles.length} document(s)
                  </Typography>
                  <List dense>
                    {providedFiles.slice(0, 5).map((file, idx) => (
                      <ListItem key={idx}>
                        <ListItemIcon>
                          <InsertDriveFile fontSize="small" />
                        </ListItemIcon>
                        <ListItemText 
                          primary={file.name}
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItem>
                    ))}
                    {providedFiles.length > 5 && (
                      <ListItem>
                        <ListItemText 
                          primary={`... and ${providedFiles.length - 5} more`}
                          primaryTypographyProps={{ variant: 'body2', color: 'text.secondary' }}
                        />
                      </ListItem>
                    )}
                  </List>
                </Box>
              )}
            </Paper>
          </Grid>
        </Grid>

        {/* Analyze Button */}
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Button
            variant="contained"
            size="large"
            onClick={handleAnalyze}
            disabled={loading || rfpFiles.length === 0 || providedFiles.length === 0}
            sx={{ px: 6, py: 2, fontSize: '1.1rem' }}
          >
            {loading ? 'Analyzing...' : '🔍 Analyze All RFPs'}
          </Button>
          {loading && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Processing {rfpFiles.length} RFP(s) against {providedFiles.length} document(s)... {progress}%
              </Typography>
              <LinearProgress variant="determinate" value={progress} />
            </Box>
          )}
        </Box>

        {/* UPDATED: Results Section - Show per RFP */}
        {results && (
          <Box>
            <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
              <Typography variant="h5" gutterBottom>
                📊 Batch Analysis Results
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Batch ID: {results.batch_id}
              </Typography>
              
              {/* Overall Stats */}
              <Grid container spacing={2} sx={{ mt: 2, mb: 3 }}>
                <Grid item xs={6} sm={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h4" color="primary">
                        {results.total_rfps}
                      </Typography>
                      <Typography variant="body2">RFPs Analyzed</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h4" color="info.main">
                        {providedFiles.length}
                      </Typography>
                      <Typography variant="body2">Documents Checked</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h4" color="success.main">
                        {results.rfp_results.reduce((sum, r) => sum + r.present, 0)}
                      </Typography>
                      <Typography variant="body2">Total Matches</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h4" color="text.secondary">
                        ${results.total_cost.toFixed(4)}
                      </Typography>
                      <Typography variant="body2">API Cost</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              {/* Download All Button */}
              <Button
                variant="outlined"
                startIcon={<CloudUpload />}
                onClick={downloadCSV}
                sx={{ mb: 2 }}
              >
                📥 Download All Results (CSV)
              </Button>

              <Divider sx={{ my: 3 }} />

              {/* Individual RFP Results (Accordions) */}
              <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                Individual RFP Results
              </Typography>

              {results.rfp_results.map((rfpResult, rfpIdx) => (
                <Accordion key={rfpIdx} defaultExpanded={results.rfp_results.length === 1}>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', gap: 2 }}>
                      <Description color="primary" />
                      <Typography variant="h6" sx={{ flexGrow: 1 }}>
                        {rfpResult.rfp_filename}
                      </Typography>
                      <Chip
                        label={`${rfpResult.completion_rate.toFixed(0)}% Complete`}
                        color={
                          rfpResult.completion_rate >= 80 
                            ? 'success' 
                            : rfpResult.completion_rate >= 60 
                            ? 'warning' 
                            : 'error'
                        }
                        size="small"
                      />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    {/* Stats for this RFP */}
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                      <Grid item xs={3}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h5">{rfpResult.total}</Typography>
                            <Typography variant="body2">Required</Typography>
                          </CardContent>
                        </Card>
                      </Grid>
                      <Grid item xs={3}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h5" color="success.main">
                              {rfpResult.present}
                            </Typography>
                            <Typography variant="body2">✅ Present</Typography>
                          </CardContent>
                        </Card>
                      </Grid>
                      <Grid item xs={3}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h5" color="warning.main">
                              {rfpResult.review}
                            </Typography>
                            <Typography variant="body2">⚠️ Review</Typography>
                          </CardContent>
                        </Card>
                      </Grid>
                      <Grid item xs={3}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h5" color="error.main">
                              {rfpResult.missing}
                            </Typography>
                            <Typography variant="body2">❌ Missing</Typography>
                          </CardContent>
                        </Card>
                      </Grid>
                    </Grid>

                    {/* Completion Progress Bar */}
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="body2" gutterBottom>
                        Completion Rate: {rfpResult.completion_rate.toFixed(1)}%
                      </Typography>
                      <LinearProgress
                        variant="determinate"
                        value={rfpResult.completion_rate}
                        color={
                          rfpResult.completion_rate >= 80
                            ? 'success'
                            : rfpResult.completion_rate >= 60
                            ? 'warning'
                            : 'error'
                        }
                        sx={{ height: 10, borderRadius: 5 }}
                      />
                    </Box>

                    {/* Results Table */}
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell width="25%"><strong>Required Document</strong></TableCell>
                            <TableCell width="35%"><strong>Description</strong></TableCell>
                            <TableCell width="15%"><strong>Status</strong></TableCell>
                            <TableCell width="25%"><strong>Matched File</strong></TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {rfpResult.matches.map((match, matchIdx) => (
                            <TableRow key={matchIdx}>
                              <TableCell>
                                <Typography variant="body2" fontWeight="medium">
                                  {match.required_document}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem', lineHeight: 1.5 }}>
                                  {match.description || "No description available"}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Chip 
                                  label={match.status}
                                  color={getStatusColor(match.status)}
                                  size="small"
                                />
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2">
                                  {match.matched_file}
                                </Typography>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>

                    {/* Download Single RFP CSV */}
                    <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => downloadSingleRfpCSV(rfpResult)}
                      >
                        📥 Download CSV
                      </Button>
                      <Typography variant="caption" color="text.secondary">
                        💰 Cost: ${rfpResult.extraction_cost.toFixed(4)}
                      </Typography>
                    </Box>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Paper>

            {/* Action Buttons */}
            <Box sx={{ textAlign: 'center' }}>
              <Button
                variant="contained"
                onClick={() => {
                  setResults(null);
                  setRfpFiles([]);
                  setProvidedFiles([]);
                }}
                sx={{ mr: 2 }}
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
          </Box>
        )}
      </Container>
    </>
  );
}
