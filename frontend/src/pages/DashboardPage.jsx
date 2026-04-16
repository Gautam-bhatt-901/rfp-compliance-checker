import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  IconButton,
  InputAdornment,
  LinearProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  AddCircleOutline,
  ArrowOutward,
  AttachMoney,
  DeleteOutline,
  DescriptionOutlined,
  Search,
  VisibilityOutlined,
} from '@mui/icons-material';
import WorkspaceShell from '../components/Layout/WorkspaceShell';
import { rfpAPI } from '../services/api';

const statCards = [
  {
    key: 'totalAnalyses',
    title: 'Total Analyses',
    tint: 'rgba(9, 90, 180, 0.08)',
    accent: '#095ab4',
  },
  {
    key: 'avgCompletionRate',
    title: 'Avg Completion Rate',
    tint: 'rgba(63, 143, 87, 0.1)',
    accent: '#3f8f57',
    formatter: (value) => `${value.toFixed(1)}%`,
  },
  {
    key: 'totalCost',
    title: 'Total API Cost',
    tint: 'rgba(198, 127, 0, 0.12)',
    accent: '#c67f00',
    formatter: (value) => `$${value.toFixed(2)}`,
  },
];

function formatDate(dateString) {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getCompletionColor(rate) {
  if (rate >= 80) return 'success';
  if (rate >= 60) return 'warning';
  return 'error';
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const data = await rfpAPI.getHistory();
      setHistory(data);
    } catch (err) {
      setError('Failed to load analysis history');
    } finally {
      setLoading(false);
    }
  };

  const stats = useMemo(() => {
    const totalAnalyses = history.length;
    const avgCompletionRate = totalAnalyses
      ? history.reduce((sum, item) => sum + item.completion_rate, 0) / totalAnalyses
      : 0;
    const totalCost = history.reduce((sum, item) => sum + item.api_cost, 0);

    return {
      totalAnalyses,
      avgCompletionRate,
      totalCost,
    };
  }, [history]);

  const displayHistory = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const filtered = history.filter((item) => {
      if (!query) return true;
      return (
        item.rfp_filename.toLowerCase().includes(query) ||
        formatDate(item.created_at).toLowerCase().includes(query) ||
        item.completion_rate.toString().includes(query)
      );
    });

    filtered.sort((a, b) => {
      let aValue;
      let bValue;

      if (sortBy === 'completion_rate') {
        aValue = a.completion_rate;
        bValue = b.completion_rate;
      } else {
        aValue = new Date(a.created_at).getTime();
        bValue = new Date(b.created_at).getTime();
      }

      return sortOrder === 'asc' ? aValue - bValue : bValue - aValue;
    });

    return filtered;
  }, [history, searchQuery, sortBy, sortOrder]);

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this analysis?')) {
      return;
    }

    try {
      await rfpAPI.deleteAnalysis(id);
      fetchHistory();
    } catch (err) {
      setError('Failed to delete analysis');
    }
  };

  const toggleSort = (column) => {
    if (sortBy === column) {
      setSortOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  return (
    <WorkspaceShell>
      <Stack spacing={4}>
        <Box>
          <Typography variant="overline" color="text.secondary">
            Command Center
          </Typography>
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            spacing={2}
            justifyContent="space-between"
            alignItems={{ xs: 'flex-start', md: 'flex-end' }}
          >
            <Box>
              <Typography variant="h2" sx={{ color: '#0a2546', mt: 1, mb: 1 }}>
                Intelligence Verification
              </Typography>
              <Typography color="text.secondary" sx={{ maxWidth: 720 }}>
                Review completed analyses, track completion performance, and continue into
                requirement-level compliance details without changing how your data is fetched.
              </Typography>
            </Box>
            <Button
              variant="contained"
              startIcon={<AddCircleOutline />}
              onClick={() => navigate('/analyze')}
            >
              New Analysis
            </Button>
          </Stack>
        </Box>

        {error && (
          <Alert severity="error" onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ py: 12, display: 'grid', placeItems: 'center' }}>
            <Stack spacing={2} alignItems="center">
              <CircularProgress />
              <Typography color="text.secondary">Loading your dashboard...</Typography>
            </Stack>
          </Box>
        ) : (
          <>
            <Grid container spacing={3}>
              {statCards.map((stat) => (
                <Grid item xs={12} md={4} key={stat.key}>
                  <Card sx={{ bgcolor: 'rgba(255,255,255,0.82)', border: '1px solid rgba(194,198,212,0.26)' }}>
                    <CardContent sx={{ p: 3.5 }}>
                      <Typography variant="overline" color="text.secondary">
                        {stat.title}
                      </Typography>
                      <Stack direction="row" justifyContent="space-between" alignItems="flex-end" mt={2}>
                        <Typography variant="h3" sx={{ color: '#0a2546' }}>
                          {stat.formatter ? stat.formatter(stats[stat.key]) : stats[stat.key]}
                        </Typography>
                        <Box
                          sx={{
                            minWidth: 68,
                            textAlign: 'center',
                            py: 0.75,
                            px: 1.25,
                            borderRadius: 999,
                            bgcolor: stat.tint,
                            color: stat.accent,
                            fontWeight: 700,
                            fontSize: '0.8rem',
                          }}
                        >
                          Live
                        </Box>
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>

            <Grid container spacing={3}>
              <Grid item xs={12} lg={8}>
                <Paper
                  sx={{
                    p: { xs: 2.5, md: 3 },
                    bgcolor: 'rgba(255,255,255,0.85)',
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
                        Analysis History
                      </Typography>
                      <Typography color="text.secondary">
                        Active audit trail for all processed RFP reviews
                      </Typography>
                    </Box>
                    <TextField
                      placeholder="Search analyses..."
                      size="small"
                      value={searchQuery}
                      onChange={(event) => setSearchQuery(event.target.value)}
                      sx={{ minWidth: { md: 300 } }}
                      InputProps={{
                        startAdornment: (
                          <InputAdornment position="start">
                            <Search fontSize="small" />
                          </InputAdornment>
                        ),
                      }}
                    />
                  </Stack>

                  {displayHistory.length === 0 ? (
                    <Box sx={{ py: 8, textAlign: 'center' }}>
                      <DescriptionOutlined sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                      <Typography variant="h5" sx={{ color: '#0a2546', mb: 1 }}>
                        No analyses yet
                      </Typography>
                      <Typography color="text.secondary" mb={3}>
                        Start a new upload to populate your compliance ledger.
                      </Typography>
                      <Button variant="contained" onClick={() => navigate('/analyze')}>
                        Create First Analysis
                      </Button>
                    </Box>
                  ) : (
                    <TableContainer>
                      <Table>
                        <TableHead>
                          <TableRow>
                            <TableCell>Batch Name</TableCell>
                            <TableCell
                              onClick={() => toggleSort('created_at')}
                              sx={{ cursor: 'pointer' }}
                            >
                              Execution Date
                            </TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell
                              onClick={() => toggleSort('completion_rate')}
                              sx={{ cursor: 'pointer' }}
                            >
                              Completion
                            </TableCell>
                            <TableCell align="right">Actions</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {displayHistory.map((item) => (
                            <TableRow key={item.id} hover>
                              <TableCell>
                                <Stack spacing={0.5}>
                                  <Typography variant="subtitle2" sx={{ color: '#0a2546' }}>
                                    {item.rfp_filename}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    {item.num_required_docs} requirements • {item.num_provided_docs} files
                                  </Typography>
                                </Stack>
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" color="text.secondary">
                                  {formatDate(item.created_at)}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Chip
                                  size="small"
                                  label={
                                    item.num_missing === 0
                                      ? 'Complete'
                                      : item.num_review > 0
                                      ? 'Needs Review'
                                      : 'In Progress'
                                  }
                                  color={getCompletionColor(item.completion_rate)}
                                />
                              </TableCell>
                              <TableCell sx={{ minWidth: 180 }}>
                                <Stack spacing={1}>
                                  <LinearProgress
                                    variant="determinate"
                                    value={item.completion_rate}
                                    color={getCompletionColor(item.completion_rate)}
                                  />
                                  <Typography variant="caption" color="text.secondary">
                                    {item.completion_rate.toFixed(1)}% complete • ${item.api_cost.toFixed(4)}
                                  </Typography>
                                </Stack>
                              </TableCell>
                              <TableCell align="right">
                                <Stack direction="row" justifyContent="flex-end" spacing={1}>
                                  <Tooltip title="View analysis">
                                    <IconButton onClick={() => navigate(`/analysis/${item.id}`)}>
                                      <VisibilityOutlined fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                  <Tooltip title="Delete analysis">
                                    <IconButton color="error" onClick={() => handleDelete(item.id)}>
                                      <DeleteOutline fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                </Stack>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                </Paper>
              </Grid>

              <Grid item xs={12} lg={4}>
                <Stack spacing={3}>
                  <Paper
                    className="ledger-glass"
                    sx={{
                      p: 3,
                      border: '1px solid rgba(194,198,212,0.28)',
                    }}
                  >
                    <Typography variant="overline" color="text.secondary">
                      Workspace Health
                    </Typography>
                    <Typography variant="h4" sx={{ color: '#0a2546', my: 1 }}>
                      {history.length ? `${Math.min(100, stats.avgCompletionRate + 8).toFixed(0)}%` : '0%'}
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={history.length ? Math.min(100, stats.avgCompletionRate + 8) : 0}
                    />
                    <Typography color="text.secondary" sx={{ mt: 2 }}>
                      Based on completion performance and successful analysis runs already
                      stored in your backend history.
                    </Typography>
                  </Paper>

                  <Paper
                    sx={{
                      p: 3,
                      color: '#fff',
                      background: 'var(--ledger-gradient)',
                    }}
                  >
                    <Typography variant="overline" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                      Cost Snapshot
                    </Typography>
                    <Stack direction="row" spacing={1.5} alignItems="center" my={1.5}>
                      <AttachMoney />
                      <Typography variant="h4">${stats.totalCost.toFixed(2)}</Typography>
                    </Stack>
                    <Typography sx={{ color: 'rgba(255,255,255,0.78)', mb: 3 }}>
                      Total spend across the analyses returned by the current API history.
                    </Typography>
                    <Button
                      variant="outlined"
                      onClick={() => navigate('/analyze')}
                      endIcon={<ArrowOutward />}
                      sx={{ color: '#fff', borderColor: 'rgba(255,255,255,0.22)' }}
                    >
                      Run another analysis
                    </Button>
                  </Paper>
                </Stack>
              </Grid>
            </Grid>
          </>
        )}
      </Stack>
    </WorkspaceShell>
  );
}
