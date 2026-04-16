import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
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
  ArrowBack,
  Download,
} from '@mui/icons-material';
import WorkspaceShell from '../components/Layout/WorkspaceShell';
import { rfpAPI } from '../services/api';

function getStatusColor(status) {
  if (status.includes('Present')) return 'success';
  if (status.includes('Missing')) return 'error';
  return 'warning';
}

export default function AnalysisDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchAnalysisDetail();
  }, [id]);

  const fetchAnalysisDetail = async () => {
    try {
      setLoading(true);
      const data = await rfpAPI.getAnalysisDetail(id);
      if (data.results_json && typeof data.results_json === 'string') {
        data.results_json = JSON.parse(data.results_json);
      }
      setAnalysis(data);
    } catch (err) {
      setError('Failed to load analysis details');
    } finally {
      setLoading(false);
    }
  };

  const matches = useMemo(() => analysis?.results_json?.matches || [], [analysis]);

  const downloadCSV = () => {
    if (!analysis || matches.length === 0) return;

    const headers = ['Required Document', 'Description', 'Status', 'Matched File'];
    const rows = matches.map((match) => {
      const description = (match.description || '').replace(/"/g, '""');
      return [`"${match.required_document}"`, `"${description}"`, `"${match.status}"`, `"${match.matched_file}"`];
    });

    const csv = [headers.map((header) => `"${header}"`).join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `analysis_${id}_results.csv`;
    anchor.click();
  };

  return (
    <WorkspaceShell>
      {loading ? (
        <Box sx={{ py: 12, display: 'grid', placeItems: 'center' }}>
          <Stack spacing={2} alignItems="center">
            <CircularProgress />
            <Typography color="text.secondary">Loading analysis details...</Typography>
          </Stack>
        </Box>
      ) : error || !analysis ? (
        <Stack spacing={3}>
          <Alert severity="error">{error || 'Analysis not found'}</Alert>
          <Box>
            <Button startIcon={<ArrowBack />} onClick={() => navigate('/dashboard')}>
              Back to Dashboard
            </Button>
          </Box>
        </Stack>
      ) : (
        <Stack spacing={4}>
          <Box>
            <Button startIcon={<ArrowBack />} onClick={() => navigate('/dashboard')} sx={{ mb: 2 }}>
              Back to Dashboard
            </Button>
            <Stack
              direction={{ xs: 'column', lg: 'row' }}
              spacing={2}
              justifyContent="space-between"
              alignItems={{ xs: 'flex-start', lg: 'flex-end' }}
            >
              <Box>
                <Typography variant="overline" color="text.secondary">
                  Compliance Detail
                </Typography>
                <Typography variant="h2" sx={{ color: '#0a2546', mt: 1, mb: 1 }}>
                  {analysis.rfp_filename}
                </Typography>
                <Typography color="text.secondary">
                  Analyzed on {new Date(analysis.created_at).toLocaleString()}
                </Typography>
              </Box>
              <Button variant="outlined" startIcon={<Download />} onClick={downloadCSV}>
                Export CSV
              </Button>
            </Stack>
          </Box>

          <Grid container spacing={3}>
            {[
              ['Required', analysis.num_required_docs],
              ['Provided', analysis.num_provided_docs],
              ['Matched', analysis.num_matched],
              ['Review', analysis.num_review],
              ['Missing', analysis.num_missing],
              ['API Cost', `$${analysis.api_cost.toFixed(4)}`],
            ].map(([label, value]) => (
              <Grid item xs={6} md={4} lg={2} key={label}>
                <Card sx={{ height: '100%', bgcolor: 'rgba(255,255,255,0.85)', border: '1px solid rgba(194,198,212,0.26)' }}>
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

          <Paper
            sx={{
              p: { xs: 2.5, md: 3 },
              bgcolor: 'rgba(255,255,255,0.88)',
              border: '1px solid rgba(194,198,212,0.28)',
            }}
          >
            <Stack direction="row" justifyContent="space-between" spacing={2} mb={2}>
              <Box>
                <Typography variant="h4" sx={{ color: '#0a2546', mb: 0.5 }}>
                  Overall Completion
                </Typography>
                <Typography color="text.secondary">
                  Derived from the saved backend analysis record
                </Typography>
              </Box>
              <Typography variant="h4" sx={{ color: '#0a2546' }}>
                {analysis.completion_rate.toFixed(1)}%
              </Typography>
            </Stack>
            <LinearProgress variant="determinate" value={analysis.completion_rate} />
          </Paper>

          <Paper
            sx={{
              p: { xs: 2.5, md: 3 },
              bgcolor: 'rgba(255,255,255,0.88)',
              border: '1px solid rgba(194,198,212,0.28)',
            }}
          >
            <Typography variant="h4" sx={{ color: '#0a2546', mb: 1 }}>
              Detailed Results
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 3 }}>
              Requirement-level matches from the stored `results_json` payload
            </Typography>

            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Requirement</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Confidence</TableCell>
                    <TableCell>Matched File</TableCell>
                    <TableCell>AI Reasoning</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {matches.map((match, index) => {
                    const confidenceValue =
                      typeof match.confidence_score === 'number'
                        ? Math.round(match.confidence_score * 100)
                        : match.status.includes('Present')
                        ? 100
                        : match.status.includes('Missing')
                        ? 5
                        : 65;

                    return (
                      <TableRow key={`${match.required_document}-${index}`} hover>
                        <TableCell>
                          <Typography variant="subtitle2" sx={{ color: '#0a2546' }}>
                            REQ-{String(index + 1).padStart(3, '0')}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ maxWidth: 320 }}>
                          <Typography variant="subtitle2" sx={{ color: '#0a2546', mb: 0.5 }}>
                            {match.required_document}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {match.description || 'No description available'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip label={match.status} size="small" color={getStatusColor(match.status)} />
                        </TableCell>
                        <TableCell sx={{ minWidth: 130 }}>
                          <Stack spacing={1}>
                            <LinearProgress
                              variant="determinate"
                              value={confidenceValue}
                              color={getStatusColor(match.status)}
                            />
                            <Typography variant="caption" color="text.secondary">
                              {confidenceValue}% confidence
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell>{match.matched_file || 'N/A'}</TableCell>
                        <TableCell sx={{ maxWidth: 360 }}>
                          <Typography variant="body2" color="text.secondary">
                            {match.details || match.description || 'No additional reasoning provided'}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Stack>
      )}
    </WorkspaceShell>
  );
}
