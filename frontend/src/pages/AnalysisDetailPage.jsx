/**
 * Analysis detail page - View past analysis results
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Grid,
  Card,
  CardContent,
  Fade,
  Zoom,
  LinearProgress,
} from '@mui/material';
import { ArrowBack, Download, CheckCircle, Warning, Cancel, Assessment } from '@mui/icons-material';
import { rfpAPI } from '../services/api';
import Navbar from '../components/Layout/Navbar';

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
      const data = await rfpAPI.getAnalysisDetail(id);
      if (data.results_json && typeof data.results_json === 'string') {
        data.results_json = JSON.parse(data.results_json);
      }
      setAnalysis(data);
    } catch (err) {
      setError('Failed to load analysis details');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const downloadCSV = () => {
    if (!analysis || !analysis.results_json || !analysis.results_json.matches) return;

    const headers = ["Required Document", "Description", "Status", "Matched File"];
    const rows = analysis.results_json.matches.map(m => {
      const description = (m.description || "").replace(/"/g, '""');
      return [
        `"${m.required_document}"`,
        `"${description}"`,
        `"${m.status}"`,
        `"${m.matched_file}"`
      ];
    });

    const csv = [headers.map(h => `"${h}"`).join(","), ...rows.map(row => row.join(","))].join("\n");
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis_${id}_results.csv`;
    a.click();
  };

  const getStatusColor = (status) => {
    if (status.includes('Present')) return 'success';
    if (status.includes('Missing')) return 'error';
    return 'warning';
  };

  if (loading) {
    return (
      <>
        <Navbar />
        <Container maxWidth="xl" sx={{ mt: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
          <Box textAlign="center">
            <CircularProgress size={60} thickness={4} sx={{ color: 'primary.main' }} />
            <Typography variant="h6" color="text.secondary" sx={{ mt: 3 }}>
              Loading analysis details...
            </Typography>
          </Box>
        </Container>
      </>
    );
  }

  if (error || !analysis) {
    return (
      <>
        <Navbar />
        <Container maxWidth="xl" sx={{ mt: 4 }}>
          <Alert severity="error" sx={{ borderRadius: 3, boxShadow: '0 4px 12px rgba(239, 68, 68, 0.2)' }}>
            {error || 'Analysis not found'}
          </Alert>
          <Button
            variant="contained"
            startIcon={<ArrowBack />}
            onClick={() => navigate('/dashboard')}
            sx={{ mt: 2 }}
          >
            Back to Dashboard
          </Button>
        </Container>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        {/* Back Button */}
        <Fade in timeout={400}>
          <Button
            variant="outlined"
            startIcon={<ArrowBack />}
            onClick={() => navigate('/dashboard')}
            sx={{
              mb: 3,
              fontWeight: 700,
              borderWidth: 2,
              '&:hover': {
                borderWidth: 2,
                transform: 'translateX(-4px)',
              },
            }}
          >
            Back to Dashboard
          </Button>
        </Fade>

        {/* Header */}
        <Fade in timeout={600}>
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
            <Typography variant="h3" fontWeight={900} gutterBottom>
              📄 Analysis Details
            </Typography>
            <Typography variant="h5" sx={{ opacity: 0.9, mb: 1 }}>
              {analysis.rfp_filename}
            </Typography>
            <Typography variant="body1" sx={{ opacity: 0.9 }}>
              Analyzed on {new Date(analysis.created_at).toLocaleString()}
            </Typography>
          </Paper>
        </Fade>

        {/* Statistics */}
        <Grid container spacing={3} mb={4}>
          {[
            { label: 'Required', value: analysis.num_required_docs, color: '#6366f1', icon: <Assessment /> },
            { label: 'Provided', value: analysis.num_provided_docs, color: '#3b82f6', icon: <Assessment /> },
            { label: '✅ Matched', value: analysis.num_matched, color: '#10b981', icon: <CheckCircle /> },
            { label: '⚠️ Review', value: analysis.num_review, color: '#f59e0b', icon: <Warning /> },
            { label: '❌ Missing', value: analysis.num_missing, color: '#ef4444', icon: <Cancel /> },
            { label: 'Complete', value: `${analysis.completion_rate.toFixed(0)}%`, color: '#ec4899', icon: <Assessment /> },
          ].map((stat, idx) => (
            <Grid item xs={6} sm={4} md={2} key={idx}>
              <Zoom in timeout={400 + idx * 100}>
                <Card
                  sx={{
                    height: '100%',
                    borderRadius: 3,
                    background: `${stat.color}10`,
                    border: `2px solid ${stat.color}30`,
                    transition: 'all 0.3s',
                    '&:hover': {
                      transform: 'scale(1.05)',
                      boxShadow: `0 8px 24px ${stat.color}40`,
                    },
                  }}
                >
                  <CardContent sx={{ textAlign: 'center', p: 2.5 }}>
                    <Box sx={{ color: stat.color, mb: 1 }}>{stat.icon}</Box>
                    <Typography variant="h4" fontWeight={900} color={stat.color}>
                      {stat.value}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" fontWeight={600}>
                      {stat.label}
                    </Typography>
                  </CardContent>
                </Card>
              </Zoom>
            </Grid>
          ))}
        </Grid>

        {/* Completion Progress */}
        <Fade in timeout={1000}>
          <Paper sx={{ p: 3, borderRadius: 4, mb: 4, boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)' }}>
            <Box display="flex" justifyContent="space-between" mb={2}>
              <Typography variant="h6" fontWeight={800}>
                Overall Completion
              </Typography>
              <Typography variant="h6" fontWeight={800} color="primary">
                {analysis.completion_rate.toFixed(1)}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={analysis.completion_rate}
              color={analysis.completion_rate >= 80 ? 'success' : analysis.completion_rate >= 60 ? 'warning' : 'error'}
              sx={{
                height: 16,
                borderRadius: 8,
                bgcolor: '#e2e8f0',
                '& .MuiLinearProgress-bar': {
                  borderRadius: 8,
                },
              }}
            />
          </Paper>
        </Fade>

        {/* Results Table */}
        {analysis.results_json && (
          <Fade in timeout={1200}>
            <Paper sx={{ p: 4, borderRadius: 4, boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)' }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h5" fontWeight={800}>
                  Detailed Results
                </Typography>
                <Button
                  variant="contained"
                  startIcon={<Download />}
                  onClick={downloadCSV}
                  sx={{
                    px: 3,
                    py: 1.5,
                    borderRadius: 3,
                    background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                    boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)',
                    fontWeight: 700,
                  }}
                >
                  Download CSV
                </Button>
              </Box>

              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow sx={{ bgcolor: '#f8fafc' }}>
                      <TableCell sx={{ fontWeight: 700, fontSize: '0.95rem' }}>Required Document</TableCell>
                      <TableCell sx={{ fontWeight: 700, fontSize: '0.95rem' }}>Description</TableCell>
                      <TableCell sx={{ fontWeight: 700, fontSize: '0.95rem' }}>Status</TableCell>
                      <TableCell sx={{ fontWeight: 700, fontSize: '0.95rem' }}>Matched File</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {analysis.results_json.matches.map((match, idx) => (
                      <Fade in timeout={200 + idx * 50} key={idx}>
                        <TableRow
                          hover
                          sx={{
                            '&:hover': {
                              bgcolor: '#f8fafc',
                              transform: 'scale(1.005)',
                              transition: 'all 0.2s',
                            },
                          }}
                        >
                          <TableCell>
                            <Typography variant="body2" fontWeight={700}>
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
                              sx={{ fontWeight: 700 }}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" fontWeight={600}>
                              {match.matched_file}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      </Fade>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Fade>
        )}

        {/* Footer Actions */}
        <Fade in timeout={1400}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mt={4}>
            <Button
              variant="outlined"
              startIcon={<ArrowBack />}
              onClick={() => navigate('/dashboard')}
              size="large"
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
              Back to Dashboard
            </Button>
            {analysis.api_cost > 0 && (
              <Paper
                sx={{
                  px: 3,
                  py: 1.5,
                  borderRadius: 3,
                  background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                  border: '2px solid #fbbf24',
                }}
              >
                <Typography variant="body1" fontWeight={700} color="#92400e">
                  💰 API Cost: ${analysis.api_cost.toFixed(4)}
                </Typography>
              </Paper>
            )}
          </Box>
        </Fade>
      </Container>
    </>
  );
}
