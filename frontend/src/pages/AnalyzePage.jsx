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
  Fade,
  Zoom,
} from '@mui/material';
import {
  CloudUpload,
  Description,
  CheckCircle,
  InsertDriveFile,
  ExpandMore,
  Download,
  TrendingUp,
  Warning,
  Cancel,
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
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  const toggleDescription = (rfpIndex, matchIndex) => {
    const key = `${rfpIndex}-${matchIndex}`;
    setExpandedDescriptions(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

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

  const downloadCSV = () => {
    if (!results || !results.rfp_results) return;

    let csv = "RFP Filename,Required Document,Description,Status,Matched File\n";
    results.rfp_results.forEach(rfpResult => {
      rfpResult.matches.forEach(match => {
        const description = (match.description || "").replace(/"/g, '""');
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

  const downloadSingleRfpCSV = (rfpResult) => {
    const headers = ["Required Document", "Description", "Status", "Matched File"];
    const rows = rfpResult.matches.map(m => {
      const description = (m.description || "").replace(/"/g, '""');
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
        <Fade in timeout={600}>
          <Box mb={4}>
            <Typography
              variant="h3"
              fontWeight={900}
              gutterBottom
              sx={{
                background: 'linear-gradient(135deg, #6366f1 0%, #ec4899 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '-0.02em',
              }}
            >
               New RFP Analysis
            </Typography>
            <Typography variant="h6" color="text.secondary" fontWeight={400}>
              Upload multiple RFP documents and supporting files to check compliance
            </Typography>
          </Box>
        </Fade>

        {error && (
          <Fade in>
            <Alert
              severity="error"
              onClose={() => setError('')}
              sx={{
                mb: 3,
                borderRadius: 3,
                boxShadow: '0 4px 12px rgba(239, 68, 68, 0.2)',
              }}
            >
              {error}
            </Alert>
          </Fade>
        )}

        {/* Upload Section */}
        <Grid container spacing={3} mb={4}>
          {/* RFP Files Upload */}
          <Grid item xs={12} md={6}>
            <Zoom in timeout={400}>
              <Paper
                elevation={0}
                sx={{
                  p: 4,
                  borderRadius: 4,
                  border: '3px dashed',
                  borderColor: rfpFiles.length > 0 ? 'success.main' : '#e2e8f0',
                  bgcolor: rfpFiles.length > 0 ? '#f0fdf4' : 'white',
                  transition: 'all 0.3s',
                  position: 'relative',
                  overflow: 'hidden',
                  '&::before': rfpFiles.length > 0 ? {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: '4px',
                    background: 'linear-gradient(90deg, #10b981 0%, #059669 100%)',
                  } : {},
                }}
              >
                <Box textAlign="center">
                  <Box
                    sx={{
                      width: 80,
                      height: 80,
                      borderRadius: '50%',
                      background: rfpFiles.length > 0
                        ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                        : 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto',
                      mb: 3,
                      boxShadow: rfpFiles.length > 0
                        ? '0 8px 24px rgba(16, 185, 129, 0.3)'
                        : '0 8px 24px rgba(99, 102, 241, 0.3)',
                    }}
                  >
                    {rfpFiles.length > 0 ? (
                      <CheckCircle sx={{ fontSize: 40, color: 'white' }} />
                    ) : (
                      <CloudUpload sx={{ fontSize: 40, color: 'white' }} />
                    )}
                  </Box>

                  <Typography variant="h6" fontWeight={700} gutterBottom>
                    1️⃣ Upload RFP Documents
                  </Typography>
                  <Typography variant="body2" color="text.secondary" mb={3}>
                    Select one or more RFP files (PDF, Word, Text, etc.)
                  </Typography>

                  <Button
                    variant="contained"
                    component="label"
                    size="large"
                    startIcon={<CloudUpload />}
                    sx={{
                      px: 4,
                      py: 1.5,
                      borderRadius: 3,
                      background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                      boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)',
                      fontWeight: 700,
                    }}
                  >
                    Choose RFP Files
                    <input
                      type="file"
                      hidden
                      multiple
                      accept=".pdf,.doc,.docx,.txt,.md,.rtf,.odt"
                      onChange={handleRfpUpload}
                    />
                  </Button>

                  {rfpFiles.length > 0 && (
                    <Box mt={3}>
                      <Chip
                        icon={<CheckCircle />}
                        label={`✓ Loaded: ${rfpFiles.length} RFP document(s)`}
                        color="success"
                        sx={{ fontWeight: 700, mb: 2 }}
                      />
                      <List dense>
                        {rfpFiles.map((file, idx) => (
                          <ListItem key={idx} sx={{ bgcolor: '#f8fafc', borderRadius: 2, mb: 0.5 }}>
                            <ListItemIcon>
                              <Description color="primary" />
                            </ListItemIcon>
                            <ListItemText
                              primary={file.name}
                              primaryTypographyProps={{ fontWeight: 600, fontSize: '0.9rem' }}
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  )}
                </Box>
              </Paper>
            </Zoom>
          </Grid>

          {/* Supporting Documents Upload */}
          <Grid item xs={12} md={6}>
            <Zoom in timeout={600}>
              <Paper
                elevation={0}
                sx={{
                  p: 4,
                  borderRadius: 4,
                  border: '3px dashed',
                  borderColor: providedFiles.length > 0 ? 'success.main' : '#e2e8f0',
                  bgcolor: providedFiles.length > 0 ? '#f0fdf4' : 'white',
                  transition: 'all 0.3s',
                  position: 'relative',
                  overflow: 'hidden',
                  '&::before': providedFiles.length > 0 ? {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: '4px',
                    background: 'linear-gradient(90deg, #10b981 0%, #059669 100%)',
                  } : {},
                }}
              >
                <Box textAlign="center">
                  <Box
                    sx={{
                      width: 80,
                      height: 80,
                      borderRadius: '50%',
                      background: providedFiles.length > 0
                        ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                        : 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto',
                      mb: 3,
                      boxShadow: providedFiles.length > 0
                        ? '0 8px 24px rgba(16, 185, 129, 0.3)'
                        : '0 8px 24px rgba(99, 102, 241, 0.3)',
                    }}
                  >
                    {providedFiles.length > 0 ? (
                      <CheckCircle sx={{ fontSize: 40, color: 'white' }} />
                    ) : (
                      <InsertDriveFile sx={{ fontSize: 40, color: 'white' }} />
                    )}
                  </Box>

                  <Typography variant="h6" fontWeight={700} gutterBottom>
                    2️⃣ Upload Supporting Documents
                  </Typography>
                  <Typography variant="body2" color="text.secondary" mb={3}>
                    Select multiple files to check against ALL RFPs
                  </Typography>

                  <Button
                    variant="contained"
                    component="label"
                    size="large"
                    startIcon={<CloudUpload />}
                    sx={{
                      px: 4,
                      py: 1.5,
                      borderRadius: 3,
                      background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                      boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)',
                      fontWeight: 700,
                    }}
                  >
                    Choose Documents
                    <input
                      type="file"
                      hidden
                      multiple
                      accept=".pdf,.doc,.docx,.txt,.md,.rtf,.odt"
                      onChange={handleProvidedFilesUpload}
                    />
                  </Button>

                  {providedFiles.length > 0 && (
                    <Box mt={3}>
                      <Chip
                        icon={<CheckCircle />}
                        label={`✓ Loaded: ${providedFiles.length} document(s)`}
                        color="success"
                        sx={{ fontWeight: 700, mb: 2 }}
                      />
                      <List dense>
                        {providedFiles.slice(0, 5).map((file, idx) => (
                          <ListItem key={idx} sx={{ bgcolor: '#f8fafc', borderRadius: 2, mb: 0.5 }}>
                            <ListItemIcon>
                              <InsertDriveFile color="primary" />
                            </ListItemIcon>
                            <ListItemText
                              primary={file.name}
                              primaryTypographyProps={{ fontWeight: 600, fontSize: '0.9rem' }}
                            />
                          </ListItem>
                        ))}
                        {providedFiles.length > 5 && (
                          <Typography variant="body2" color="text.secondary" textAlign="center" mt={1}>
                            + {providedFiles.length - 5} more files
                          </Typography>
                        )}
                      </List>
                    </Box>
                  )}
                </Box>
              </Paper>
            </Zoom>
          </Grid>
        </Grid>

        {/* Analyze Button */}
        <Fade in timeout={800}>
          <Box textAlign="center" mb={4}>
            <Button
              variant="contained"
              size="large"
              onClick={handleAnalyze}
              disabled={loading || rfpFiles.length === 0 || providedFiles.length === 0}
              sx={{
                px: 6,
                py: 2,
                fontSize: '1.2rem',
                fontWeight: 800,
                borderRadius: 3,
                background: 'linear-gradient(135deg, #6366f1 0%, #ec4899 100%)',
                boxShadow: '0 12px 40px rgba(99, 102, 241, 0.4)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #4f46e5 0%, #db2777 100%)',
                  boxShadow: '0 16px 48px rgba(99, 102, 241, 0.5)',
                  transform: 'translateY(-4px)',
                },
                '&:disabled': {
                  background: '#e2e8f0',
                  color: '#94a3b8',
                },
              }}
            >
              {loading ? '🔄 Analyzing...' : '🔍 Analyze All RFPs'}
            </Button>

            {loading && (
              <Box mt={3} maxWidth={600} mx="auto">
                <Typography variant="body1" color="text.secondary" mb={2} fontWeight={600}>
                  Processing {rfpFiles.length} RFP(s) against {providedFiles.length} document(s)... {progress}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={progress}
                  sx={{
                    height: 10,
                    borderRadius: 5,
                    bgcolor: '#e2e8f0',
                    '& .MuiLinearProgress-bar': {
                      background: 'linear-gradient(90deg, #6366f1 0%, #ec4899 100%)',
                      borderRadius: 5,
                    },
                  }}
                />
              </Box>
            )}
          </Box>
        </Fade>

        {/* Results Section */}
        {results && (
          <Fade in timeout={1000}>
            <Box>
              <Paper
                sx={{
                  p: 4,
                  borderRadius: 4,
                  mb: 4,
                  background: 'linear-gradient(135deg, #6366f1 0%, #ec4899 100%)',
                  color: 'white',
                  boxShadow: '0 20px 60px rgba(99, 102, 241, 0.4)',
                }}
              >
                <Typography variant="h4" fontWeight={900} gutterBottom>
                   Batch Analysis Results
                </Typography>
                <Typography variant="h6" sx={{ opacity: 0.9 }}>
                  Batch ID: {results.batch_id}
                </Typography>

                {/* Overall Stats */}
                <Grid container spacing={3} mt={2}>
                  {[
                    { label: 'RFPs Analyzed', value: results.total_rfps, icon: <Description /> },
                    { label: 'Documents Checked', value: providedFiles.length, icon: <InsertDriveFile /> },
                    { label: 'Total Matches', value: results.rfp_results.reduce((sum, r) => sum + r.present, 0), icon: <CheckCircle /> },
                    { label: 'API Cost', value: `$${results.total_cost.toFixed(4)}`, icon: <TrendingUp /> },
                  ].map((stat, idx) => (
                    <Grid item xs={12} sm={6} md={3} key={idx}>
                      <Box
                        sx={{
                          bgcolor: 'rgba(255, 255, 255, 0.2)',
                          backdropFilter: 'blur(10px)',
                          borderRadius: 3,
                          p: 2.5,
                          textAlign: 'center',
                          border: '1px solid rgba(255, 255, 255, 0.3)',
                        }}
                      >
                        <Box mb={1}>{stat.icon}</Box>
                        <Typography variant="h4" fontWeight={900}>
                          {stat.value}
                        </Typography>
                        <Typography variant="body2" sx={{ opacity: 0.9 }}>
                          {stat.label}
                        </Typography>
                      </Box>
                    </Grid>
                  ))}
                </Grid>

                {/* Download All Button */}
                <Box mt={3}>
                  <Button
                    variant="contained"
                    startIcon={<Download />}
                    onClick={downloadCSV}
                    sx={{
                      bgcolor: 'white',
                      color: '#6366f1',
                      fontWeight: 700,
                      px: 4,
                      py: 1.5,
                      '&:hover': {
                        bgcolor: '#f8fafc',
                      },
                    }}
                  >
                    📥 Download All Results (CSV)
                  </Button>
                </Box>
              </Paper>

              {/* Individual RFP Results */}
              <Typography variant="h5" fontWeight={800} mb={3} color="text.primary">
                Individual RFP Results
              </Typography>

              {results.rfp_results.map((rfpResult, rfpIdx) => (
                <Accordion
                  key={rfpIdx}
                  defaultExpanded={rfpIdx === 0}
                  sx={{
                    mb: 2,
                    borderRadius: 3,
                    '&:before': { display: 'none' },
                    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
                  }}
                >
                  <AccordionSummary
                    expandIcon={<ExpandMore />}
                    sx={{
                      bgcolor: '#f8fafc',
                      borderRadius: 3,
                      '&:hover': { bgcolor: '#f1f5f9' },
                    }}
                  >
                    <Box display="flex" alignItems="center" gap={2} width="100%">
                      <Description color="primary" />
                      <Typography variant="h6" fontWeight={700} sx={{ flexGrow: 1 }}>
                        {rfpResult.rfp_filename}
                      </Typography>
                      <Chip
                        label={`${rfpResult.completion_rate.toFixed(1)}%`}
                        color={
                          rfpResult.completion_rate >= 80
                            ? 'success'
                            : rfpResult.completion_rate >= 60
                            ? 'warning'
                            : 'error'
                        }
                        size="small"
                        sx={{ fontWeight: 700 }}
                      />
                    </Box>
                  </AccordionSummary>

                  <AccordionDetails sx={{ p: 3 }}>
                    {/* Stats for this RFP */}
                    <Grid container spacing={2} mb={3}>
                      {[
                        { label: 'Required', value: rfpResult.total, color: '#6366f1' },
                        { label: '✅ Present', value: rfpResult.present, color: '#10b981' },
                        { label: '⚠️ Review', value: rfpResult.review, color: '#f59e0b' },
                        { label: '❌ Missing', value: rfpResult.missing, color: '#ef4444' },
                      ].map((stat, idx) => (
                        <Grid item xs={6} sm={3} key={idx}>
                          <Box
                            sx={{
                              bgcolor: `${stat.color}10`,
                              borderRadius: 2,
                              p: 2,
                              textAlign: 'center',
                              border: `2px solid ${stat.color}30`,
                            }}
                          >
                            <Typography variant="h5" fontWeight={800} color={stat.color}>
                              {stat.value}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" fontWeight={600}>
                              {stat.label}
                            </Typography>
                          </Box>
                        </Grid>
                      ))}
                    </Grid>

                    {/* Completion Progress Bar */}
                    <Box mb={3}>
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2" fontWeight={700}>
                          Completion Rate
                        </Typography>
                        <Typography variant="body2" fontWeight={700} color="primary">
                          {rfpResult.completion_rate.toFixed(1)}%
                        </Typography>
                      </Box>
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
                    <TableContainer component={Paper} elevation={0} sx={{ borderRadius: 3, border: '1px solid #e2e8f0' }}>
                      <Table>
                        <TableHead>
                          <TableRow sx={{ bgcolor: '#f8fafc' }}>
                            <TableCell sx={{ fontWeight: 700 }}>Required Document</TableCell>
                            <TableCell sx={{ fontWeight: 700 }}>Description</TableCell>
                            <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                            <TableCell sx={{ fontWeight: 700 }}>Matched File</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {rfpResult.matches.map((match, matchIdx) => (
                            <TableRow key={matchIdx} hover>
                              <TableCell>
                                <Typography variant="body2" fontWeight={600}>
                                  {match.required_document}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" color="text.secondary">
                                  {match.description || "No description available"}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Chip
                                  label={match.status}
                                  color={getStatusColor(match.status)}
                                  size="small"
                                  sx={{ fontWeight: 600 }}
                                />
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" fontWeight={600}>
                                  {match.matched_file}
                                </Typography>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>

                    {/* Download Single RFP CSV */}
                    <Box display="flex" justifyContent="space-between" alignItems="center" mt={3}>
                      <Button
                        variant="outlined"
                        startIcon={<Download />}
                        onClick={() => downloadSingleRfpCSV(rfpResult)}
                        sx={{ fontWeight: 700 }}
                      >
                        📥 Download CSV
                      </Button>
                      <Typography variant="body2" color="text.secondary" fontWeight={600}>
                        💰 Cost: ${rfpResult.extraction_cost.toFixed(4)}
                      </Typography>
                    </Box>
                  </AccordionDetails>
                </Accordion>
              ))}

              {/* Action Buttons */}
              <Box display="flex" gap={2} justifyContent="center" mt={4}>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={() => {
                    setResults(null);
                    setRfpFiles([]);
                    setProvidedFiles([]);
                  }}
                  sx={{
                    px: 4,
                    py: 1.5,
                    borderRadius: 3,
                    fontWeight: 700,
                    borderWidth: 2,
                    '&:hover': {
                      borderWidth: 2,
                    },
                  }}
                >
                  🔄 New Analysis
                </Button>
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => navigate('/dashboard')}
                  sx={{
                    px: 4,
                    py: 1.5,
                    borderRadius: 3,
                    fontWeight: 700,
                    background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                    boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)',
                  }}
                >
                  📊 View Dashboard
                </Button>
              </Box>
            </Box>
          </Fade>
        )}
      </Container>
    </>
  );
}
