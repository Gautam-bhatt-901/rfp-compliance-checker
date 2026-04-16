import React, { useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  Divider,
  Grid,
  LinearProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import {
  AutoAwesome,
  CloudUploadOutlined,
  DeleteOutline,
  DescriptionOutlined,
  Download,
  FolderOpenOutlined,
  InsertDriveFileOutlined,
} from '@mui/icons-material';
import WorkspaceShell from '../components/Layout/WorkspaceShell';
import { rfpAPI } from '../services/api';

function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return 'Unknown';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getStatusColor(status) {
  if (status.includes('Present')) return 'success';
  if (status.includes('Missing')) return 'error';
  return 'warning';
}

export default function AnalyzePage() {
  const navigate = useNavigate();
  const rfpInputRef = useRef(null);
  const providedInputRef = useRef(null);
  const [rfpFiles, setRfpFiles] = useState([]);
  const [providedFiles, setProvidedFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  const queue = useMemo(
    () => [
      ...rfpFiles.map((file) => ({ file, type: 'Primary RFP' })),
      ...providedFiles.map((file) => ({ file, type: 'Evidence' })),
    ],
    [rfpFiles, providedFiles]
  );

  const totalMatches = results
    ? results.rfp_results.reduce((sum, item) => sum + item.present, 0)
    : 0;

  const handleRfpUpload = (event) => {
    setRfpFiles(Array.from(event.target.files));
    setResults(null);
    setError('');
  };

  const handleProvidedUpload = (event) => {
    setProvidedFiles(Array.from(event.target.files));
    setResults(null);
    setError('');
  };

  const removeQueuedFile = (type, name) => {
    if (type === 'Primary RFP') {
      setRfpFiles((files) => files.filter((file) => file.name !== name));
    } else {
      setProvidedFiles((files) => files.filter((file) => file.name !== name));
    }
    setResults(null);
  };

  const handleAnalyze = async () => {
    if (rfpFiles.length === 0 || providedFiles.length === 0) {
      setError('Please upload both RFP document(s) and supporting documents');
      return;
    }

    setLoading(true);
    setProgress(0);
    setError('');

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

  const downloadCSV = () => {
    if (!results || !results.rfp_results) return;

    let csv = 'RFP Filename,Required Document,Description,Status,Matched File\n';
    results.rfp_results.forEach((rfpResult) => {
      rfpResult.matches.forEach((match) => {
        const description = (match.description || '').replace(/"/g, '""');
        csv += `"${rfpResult.rfp_filename}","${match.required_document}","${description}","${match.status}","${match.matched_file}"\n`;
      });
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `batch_analysis_${results.batch_id}.csv`;
    anchor.click();
  };

  const downloadSingleRfpCSV = (rfpResult) => {
    const headers = ['Required Document', 'Description', 'Status', 'Matched File'];
    const rows = rfpResult.matches.map((match) => {
      const description = (match.description || '').replace(/"/g, '""');
      return [`"${match.required_document}"`, `"${description}"`, `"${match.status}"`, `"${match.matched_file}"`];
    });

    const csv = [headers.map((header) => `"${header}"`).join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${rfpResult.rfp_filename.replace('.pdf', '')}_results.csv`;
    anchor.click();
  };

  return (
    <WorkspaceShell>
      <Stack spacing={4}>
        <Box>
          <Typography variant="overline" color="text.secondary">
            Multi-RFP Command Center
          </Typography>
          <Typography variant="h2" sx={{ color: '#0a2546', mt: 1, mb: 1 }}>
            Coordinate verification workstreams
          </Typography>
          <Typography color="text.secondary" sx={{ maxWidth: 760 }}>
            Upload multiple RFP documents, add an evidence pool, and run the same
            backend-powered compliance analysis through a cleaner command-center layout.
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper
              sx={{
                p: 4,
                minHeight: 300,
                borderRadius: 6,
                bgcolor: 'rgba(255,255,255,0.88)',
                border: '1px solid rgba(194,198,212,0.3)',
              }}
            >
              <Stack height="100%" justifyContent="space-between" spacing={3}>
                <Box>
                  <Box
                    sx={{
                      width: 68,
                      height: 68,
                      borderRadius: '50%',
                      display: 'grid',
                      placeItems: 'center',
                      bgcolor: 'rgba(9, 90, 180, 0.08)',
                      color: 'primary.main',
                      mb: 3,
                    }}
                  >
                    <CloudUploadOutlined sx={{ fontSize: 34 }} />
                  </Box>
                  <Typography variant="h4" sx={{ color: '#0a2546', mb: 1 }}>
                    Upload RFP Documents
                  </Typography>
                  <Typography color="text.secondary">
                    Select one or more solicitation files. Supported formats still follow the
                    existing backend upload handling.
                  </Typography>
                </Box>
                <Box>
                  <Button variant="contained" onClick={() => rfpInputRef.current?.click()}>
                    Choose RFP Files
                  </Button>
                  <input
                    ref={rfpInputRef}
                    type="file"
                    hidden
                    multiple
                    accept=".pdf,.doc,.docx,.txt,.md,.rtf,.odt"
                    onChange={handleRfpUpload}
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                    {rfpFiles.length
                      ? `${rfpFiles.length} RFP document(s) ready for analysis`
                      : 'No RFP documents selected yet'}
                  </Typography>
                </Box>
              </Stack>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper
              sx={{
                p: 4,
                minHeight: 300,
                borderRadius: 6,
                bgcolor: 'rgba(255,255,255,0.88)',
                border: '1px solid rgba(194,198,212,0.3)',
              }}
            >
              <Stack height="100%" justifyContent="space-between" spacing={3}>
                <Box>
                  <Box
                    sx={{
                      width: 68,
                      height: 68,
                      borderRadius: '50%',
                      display: 'grid',
                      placeItems: 'center',
                      bgcolor: 'rgba(198, 127, 0, 0.12)',
                      color: '#c67f00',
                      mb: 3,
                    }}
                  >
                    <FolderOpenOutlined sx={{ fontSize: 34 }} />
                  </Box>
                  <Typography variant="h4" sx={{ color: '#0a2546', mb: 1 }}>
                    Supporting Evidence Pool
                  </Typography>
                  <Typography color="text.secondary">
                    Upload supporting documents once and use them across all selected RFPs in
                    the same analysis run.
                  </Typography>
                </Box>
                <Box>
                  <Button variant="outlined" onClick={() => providedInputRef.current?.click()}>
                    Choose Supporting Files
                  </Button>
                  <input
                    ref={providedInputRef}
                    type="file"
                    hidden
                    multiple
                    accept=".pdf,.doc,.docx,.txt,.md,.rtf,.odt"
                    onChange={handleProvidedUpload}
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                    {providedFiles.length
                      ? `${providedFiles.length} supporting file(s) loaded`
                      : 'No supporting documents selected yet'}
                  </Typography>
                </Box>
              </Stack>
            </Paper>
          </Grid>
        </Grid>

        <Paper
          sx={{
            p: { xs: 2.5, md: 3 },
            bgcolor: 'rgba(255,255,255,0.86)',
            border: '1px solid rgba(194,198,212,0.28)',
          }}
        >
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            spacing={2}
            justifyContent="space-between"
            alignItems={{ xs: 'stretch', md: 'center' }}
            mb={3}
          >
            <Box>
              <Typography variant="h4" sx={{ color: '#0a2546', mb: 0.5 }}>
                Active Analysis Queue
              </Typography>
              <Typography color="text.secondary">
                {queue.length
                  ? `${queue.length} file(s) staged for the next run`
                  : 'Add RFPs and evidence files to begin'}
              </Typography>
            </Box>
            <Button
              variant="contained"
              startIcon={<AutoAwesome />}
              onClick={handleAnalyze}
              disabled={loading || rfpFiles.length === 0 || providedFiles.length === 0}
            >
              {loading ? 'Analyzing...' : 'Start AI Analysis'}
            </Button>
          </Stack>

          {loading && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Processing {rfpFiles.length} RFP(s) against {providedFiles.length} document(s)...
                {' '}{progress}%
              </Typography>
              <LinearProgress variant="determinate" value={progress} />
            </Box>
          )}

          {queue.length === 0 ? (
            <Box sx={{ py: 5, textAlign: 'center' }}>
              <InsertDriveFileOutlined sx={{ fontSize: 46, color: 'text.secondary', mb: 2 }} />
              <Typography color="text.secondary">
                Your queued files will appear here once selected.
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>File Name</TableCell>
                    <TableCell>Classification</TableCell>
                    <TableCell>Size</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {queue.map(({ file, type }) => (
                    <TableRow key={`${type}-${file.name}`} hover>
                      <TableCell>
                        <Stack direction="row" spacing={1.5} alignItems="center">
                          <DescriptionOutlined fontSize="small" color="action" />
                          <Typography variant="subtitle2" sx={{ color: '#0a2546' }}>
                            {file.name}
                          </Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={type}
                          color={type === 'Primary RFP' ? 'info' : 'default'}
                        />
                      </TableCell>
                      <TableCell>{formatBytes(file.size)}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={loading ? 'Processing' : 'Ready'}
                          color={loading ? 'warning' : 'success'}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          color="error"
                          startIcon={<DeleteOutline />}
                          onClick={() => removeQueuedFile(type, file.name)}
                          disabled={loading}
                        >
                          Remove
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>

        {results && (
          <Stack spacing={3}>
            <Paper
              sx={{
                p: { xs: 3, md: 4 },
                color: '#fff',
                background: 'var(--ledger-gradient)',
              }}
            >
              <Stack
                direction={{ xs: 'column', md: 'row' }}
                spacing={2}
                justifyContent="space-between"
                alignItems={{ xs: 'flex-start', md: 'center' }}
                mb={3}
              >
                <Box>
                  <Typography variant="overline" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                    Batch Result
                  </Typography>
                  <Typography variant="h3" sx={{ color: '#fff', mb: 1 }}>
                    Batch Analysis Results
                  </Typography>
                  <Typography sx={{ color: 'rgba(255,255,255,0.78)' }}>
                    Batch ID: {results.batch_id}
                  </Typography>
                </Box>
                <Button
                  variant="outlined"
                  startIcon={<Download />}
                  onClick={downloadCSV}
                  sx={{ color: '#fff', borderColor: 'rgba(255,255,255,0.24)' }}
                >
                  Download All Results
                </Button>
              </Stack>

              <Grid container spacing={2}>
                {[
                  ['RFPs Analyzed', results.total_rfps],
                  ['Documents Checked', providedFiles.length],
                  ['Total Matches', totalMatches],
                  ['API Cost', `$${results.total_cost.toFixed(4)}`],
                ].map(([label, value]) => (
                  <Grid item xs={12} sm={6} md={3} key={label}>
                    <Paper
                      sx={{
                        p: 2.5,
                        bgcolor: 'rgba(255,255,255,0.08)',
                        color: '#fff',
                        border: '1px solid rgba(255,255,255,0.1)',
                      }}
                    >
                      <Typography variant="overline" sx={{ color: 'rgba(255,255,255,0.65)' }}>
                        {label}
                      </Typography>
                      <Typography variant="h4" sx={{ mt: 1 }}>
                        {value}
                      </Typography>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </Paper>

            {results.rfp_results.map((rfpResult, index) => (
              <Paper
                key={`${rfpResult.rfp_filename}-${index}`}
                sx={{
                  p: { xs: 2.5, md: 3 },
                  bgcolor: 'rgba(255,255,255,0.88)',
                  border: '1px solid rgba(194,198,212,0.28)',
                }}
              >
                <Stack
                  direction={{ xs: 'column', lg: 'row' }}
                  spacing={2}
                  justifyContent="space-between"
                  alignItems={{ xs: 'flex-start', lg: 'center' }}
                  mb={3}
                >
                  <Box>
                    <Typography variant="h4" sx={{ color: '#0a2546', mb: 0.5 }}>
                      {rfpResult.rfp_filename}
                    </Typography>
                    <Typography color="text.secondary">
                      {rfpResult.total} required documents • {rfpResult.present} present •{' '}
                      {rfpResult.review} review • {rfpResult.missing} missing
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Chip
                      label={`${rfpResult.completion_rate.toFixed(1)}% complete`}
                      color={
                        rfpResult.completion_rate >= 80
                          ? 'success'
                          : rfpResult.completion_rate >= 60
                          ? 'warning'
                          : 'error'
                      }
                    />
                    <Button
                      variant="outlined"
                      startIcon={<Download />}
                      onClick={() => downloadSingleRfpCSV(rfpResult)}
                    >
                      Download CSV
                    </Button>
                  </Stack>
                </Stack>

                <Grid container spacing={2} mb={3}>
                  {[
                    ['Required', rfpResult.total],
                    ['Present', rfpResult.present],
                    ['Review', rfpResult.review],
                    ['Missing', rfpResult.missing],
                  ].map(([label, value]) => (
                    <Grid item xs={6} md={3} key={label}>
                      <Card sx={{ bgcolor: 'rgba(242,243,251,0.8)' }}>
                        <CardContent sx={{ p: 2.5 }}>
                          <Typography variant="overline" color="text.secondary">
                            {label}
                          </Typography>
                          <Typography variant="h4" sx={{ color: '#0a2546', mt: 1 }}>
                            {value}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>

                <Box sx={{ mb: 3 }}>
                  <Stack direction="row" justifyContent="space-between" mb={1}>
                    <Typography variant="body2" color="text.secondary">
                      Completion Rate
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {rfpResult.completion_rate.toFixed(1)}%
                    </Typography>
                  </Stack>
                  <LinearProgress variant="determinate" value={rfpResult.completion_rate} />
                </Box>

                <TableContainer component={Paper} sx={{ border: '1px solid rgba(194,198,212,0.22)' }}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Required Document</TableCell>
                        <TableCell>Description</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Matched File</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {rfpResult.matches.map((match, matchIndex) => (
                        <TableRow key={`${rfpResult.rfp_filename}-${match.required_document}-${matchIndex}`} hover>
                          <TableCell>
                            <Typography variant="subtitle2" sx={{ color: '#0a2546' }}>
                              {match.required_document}
                            </Typography>
                          </TableCell>
                          <TableCell>{match.description || 'No description available'}</TableCell>
                          <TableCell>
                            <Chip label={match.status} size="small" color={getStatusColor(match.status)} />
                          </TableCell>
                          <TableCell>{match.matched_file}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>

                <Divider sx={{ my: 3 }} />
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="space-between">
                  <Typography color="text.secondary">
                    Extraction cost: ${rfpResult.extraction_cost.toFixed(4)}
                  </Typography>
                  {rfpResult.analysis_id && (
                    <Button onClick={() => navigate(`/analysis/${rfpResult.analysis_id}`)}>
                      Open saved analysis
                    </Button>
                  )}
                </Stack>
              </Paper>
            ))}
          </Stack>
        )}
      </Stack>
    </WorkspaceShell>
  );
}
