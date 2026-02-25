/**
 * Dashboard page - Shows analysis history
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  IconButton,
  Alert,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  Tooltip,
  TextField,
  InputAdornment,
  TableSortLabel,
  Fade,
  Zoom,
} from '@mui/material';
import {
  Add,
  Visibility,
  Delete,
  Assessment,
  CheckCircle,
  Warning,
  Cancel,
  Search,
  TrendingUp,
  AttachMoney,
  BarChart,
} from '@mui/icons-material';
import { rfpAPI } from '../services/api';
import Navbar from '../components/Layout/Navbar';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({
    totalAnalyses: 0,
    avgCompletionRate: 0,
    totalCost: 0,
  });

  // Search and sorting state
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

      const totalAnalyses = data.length;
      const avgCompletionRate = totalAnalyses > 0
        ? data.reduce((sum, item) => sum + item.completion_rate, 0) / totalAnalyses
        : 0;
      const totalCost = data.reduce((sum, item) => sum + item.api_cost, 0);

      setStats({ totalAnalyses, avgCompletionRate, totalCost });
    } catch (err) {
      setError('Failed to load analysis history');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleView = (id) => {
    navigate(`/analysis/${id}`);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this analysis?')) {
      try {
        await rfpAPI.deleteAnalysis(id);
        fetchHistory();
      } catch (err) {
        setError('Failed to delete analysis');
      }
    }
  };

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const getFilteredAndSortedHistory = () => {
    let filtered = history.filter((item) => {
      const searchLower = searchQuery.toLowerCase();
      return (
        item.rfp_filename.toLowerCase().includes(searchLower) ||
        formatDate(item.created_at).toLowerCase().includes(searchLower) ||
        item.completion_rate.toString().includes(searchLower)
      );
    });

    filtered.sort((a, b) => {
      let aValue, bValue;

      if (sortBy === 'created_at') {
        aValue = new Date(a.created_at).getTime();
        bValue = new Date(b.created_at).getTime();
      } else if (sortBy === 'completion_rate') {
        aValue = a.completion_rate;
        bValue = b.completion_rate;
      }

      if (sortOrder === 'asc') {
        return aValue - bValue;
      } else {
        return bValue - aValue;
      }
    });

    return filtered;
  };

  const getCompletionColor = (rate) => {
    if (rate >= 80) return 'success';
    if (rate >= 60) return 'warning';
    return 'error';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <>
        <Navbar />
        <Container maxWidth="xl" sx={{ mt: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
          <Box textAlign="center">
            <CircularProgress size={60} thickness={4} sx={{ color: 'primary.main' }} />
            <Typography variant="h6" color="text.secondary" sx={{ mt: 3 }}>
              Loading your dashboard...
            </Typography>
          </Box>
        </Container>
      </>
    );
  }

  const displayHistory = getFilteredAndSortedHistory();

  return (
    <>
      <Navbar />
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        {/* Header */}
        <Fade in timeout={600}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
            <Box>
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
                 Dashboard
              </Typography>
              <Typography variant="h6" color="text.secondary" fontWeight={400}>
                View and manage your RFP compliance analyses
              </Typography>
            </Box>
            <Button
              variant="contained"
              color="primary"
              startIcon={<Add />}
              onClick={() => navigate('/analyze')}
              size="large"
              sx={{
                px: 4,
                py: 1.5,
                borderRadius: 3,
                background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)',
                fontWeight: 700,
                fontSize: '1rem',
                '&:hover': {
                  background: 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)',
                  boxShadow: '0 12px 32px rgba(99, 102, 241, 0.5)',
                  transform: 'translateY(-2px)',
                },
              }}
            >
              New Analysis
            </Button>
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

        {/* Statistics Cards */}
        <Grid container spacing={3} mb={4}>
          {[
            {
              icon: <Assessment sx={{ fontSize: 40 }} />,
              title: 'Total Analyses',
              value: stats.totalAnalyses,
              color: '#6366f1',
              gradient: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
              delay: 200,
            },
            {
              icon: <BarChart sx={{ fontSize: 40 }} />,
              title: 'Avg Completion Rate',
              value: `${stats.avgCompletionRate.toFixed(1)}%`,
              color: '#10b981',
              gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              delay: 400,
            },
            {
              icon: <AttachMoney sx={{ fontSize: 40 }} />,
              title: 'Total API Cost',
              value: `$${stats.totalCost.toFixed(2)}`,
              color: '#f59e0b',
              gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              delay: 600,
            },
          ].map((stat, index) => (
            <Grid item xs={12} md={4} key={index}>
              <Zoom in timeout={stat.delay}>
                <Card
                  sx={{
                    height: '100%',
                    background: 'white',
                    borderRadius: 4,
                    overflow: 'hidden',
                    position: 'relative',
                    transition: 'all 0.3s',
                    '&:hover': {
                      transform: 'translateY(-8px)',
                      boxShadow: `0 20px 40px ${stat.color}30`,
                    },
                    '&::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: '4px',
                      background: stat.gradient,
                    },
                  }}
                >
                  <CardContent sx={{ p: 3 }}>
                    <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                      <Box
                        sx={{
                          width: 60,
                          height: 60,
                          borderRadius: 3,
                          background: `${stat.color}15`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: stat.color,
                        }}
                      >
                        {stat.icon}
                      </Box>
                    </Box>
                    <Typography variant="body2" color="text.secondary" fontWeight={600} mb={1}>
                      {stat.title}
                    </Typography>
                    <Typography variant="h3" fontWeight={900} color="text.primary">
                      {stat.value}
                    </Typography>
                  </CardContent>
                </Card>
              </Zoom>
            </Grid>
          ))}
        </Grid>

        {/* Analysis History Table */}
        <Fade in timeout={800}>
          <Paper
            sx={{
              p: 4,
              borderRadius: 4,
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
            }}
          >
            {/* Header with search */}
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
              <Typography variant="h5" fontWeight={800} color="text.primary">
                Analysis History
              </Typography>
              <TextField
                placeholder="Search analyses..."
                variant="outlined"
                size="small"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                sx={{
                  width: 350,
                  '& .MuiOutlinedInput-root': {
                    borderRadius: 3,
                    bgcolor: '#f8fafc',
                    '&:hover': {
                      bgcolor: 'white',
                    },
                  },
                }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search color="action" />
                    </InputAdornment>
                  ),
                }}
              />
            </Box>

            {history.length === 0 ? (
              <Box textAlign="center" py={10}>
                <Box
                  sx={{
                    width: 120,
                    height: 120,
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #6366f1 0%, #ec4899 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto',
                    mb: 3,
                    opacity: 0.9,
                  }}
                >
                  <Assessment sx={{ fontSize: 60, color: 'white' }} />
                </Box>
                <Typography variant="h5" fontWeight={700} color="text.primary" gutterBottom>
                  No analyses yet
                </Typography>
                <Typography variant="body1" color="text.secondary" mb={4}>
                  Start by uploading your first RFP document
                </Typography>
                <Button
                  variant="contained"
                  startIcon={<Add />}
                  onClick={() => navigate('/analyze')}
                  size="large"
                  sx={{
                    px: 4,
                    py: 1.5,
                    borderRadius: 3,
                    background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                    boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)',
                  }}
                >
                  Create First Analysis
                </Button>
              </Box>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700, fontSize: '0.95rem' }}>
                        RFP Document
                      </TableCell>
                      <TableCell>
                        <TableSortLabel
                          active={sortBy === 'created_at'}
                          direction={sortBy === 'created_at' ? sortOrder : 'desc'}
                          onClick={() => handleSort('created_at')}
                          sx={{ fontWeight: 700, fontSize: '0.95rem' }}
                        >
                          Date
                        </TableSortLabel>
                      </TableCell>
                      <TableCell align="center" sx={{ fontWeight: 700, fontSize: '0.95rem' }}>
                        Required Docs
                      </TableCell>
                      <TableCell align="center" sx={{ fontWeight: 700, fontSize: '0.95rem' }}>
                        Provided Docs
                      </TableCell>
                      <TableCell align="center" sx={{ fontWeight: 700, fontSize: '0.95rem' }}>
                        Matched
                      </TableCell>
                      <TableCell align="center" sx={{ fontWeight: 700, fontSize: '0.95rem' }}>
                        Review
                      </TableCell>
                      <TableCell align="center" sx={{ fontWeight: 700, fontSize: '0.95rem' }}>
                        Missing
                      </TableCell>
                      <TableCell align="center">
                        <TableSortLabel
                          active={sortBy === 'completion_rate'}
                          direction={sortBy === 'completion_rate' ? sortOrder : 'desc'}
                          onClick={() => handleSort('completion_rate')}
                          sx={{ fontWeight: 700, fontSize: '0.95rem' }}
                        >
                          Completion
                        </TableSortLabel>
                      </TableCell>
                      <TableCell align="center" sx={{ fontWeight: 700, fontSize: '0.95rem' }}>
                        Cost
                      </TableCell>
                      <TableCell align="center" sx={{ fontWeight: 700, fontSize: '0.95rem' }}>
                        Actions
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {displayHistory.map((item, index) => (
                      <Fade in timeout={200 + index * 50} key={item.id}>
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
                            <Typography variant="body2" fontWeight={600}>
                              {item.rfp_filename}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {formatDate(item.created_at)}
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Chip
                              label={item.num_required_docs}
                              size="small"
                              sx={{
                                bgcolor: '#f1f5f9',
                                color: '#475569',
                                fontWeight: 700,
                              }}
                            />
                          </TableCell>
                          <TableCell align="center">
                            <Chip
                              label={item.num_provided_docs}
                              size="small"
                              sx={{
                                bgcolor: '#dbeafe',
                                color: '#1e40af',
                                fontWeight: 700,
                              }}
                            />
                          </TableCell>
                          <TableCell align="center">
                            <Chip
                              icon={<CheckCircle sx={{ fontSize: 16 }} />}
                              label={item.num_matched}
                              color="success"
                              size="small"
                              sx={{ fontWeight: 700 }}
                            />
                          </TableCell>
                          <TableCell align="center">
                            <Chip
                              icon={<Warning sx={{ fontSize: 16 }} />}
                              label={item.num_review}
                              color="warning"
                              size="small"
                              sx={{ fontWeight: 700 }}
                            />
                          </TableCell>
                          <TableCell align="center">
                            <Chip
                              icon={<Cancel sx={{ fontSize: 16 }} />}
                              label={item.num_missing}
                              color="error"
                              size="small"
                              sx={{ fontWeight: 700 }}
                            />
                          </TableCell>
                          <TableCell align="center">
                            <Chip
                              label={`${item.completion_rate.toFixed(1)}%`}
                              color={getCompletionColor(item.completion_rate)}
                              size="small"
                              sx={{
                                fontWeight: 700,
                                minWidth: 60,
                              }}
                            />
                          </TableCell>
                          <TableCell align="center">
                            <Typography variant="body2" fontWeight={600} color="text.secondary">
                              ${item.api_cost.toFixed(4)}
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Box display="flex" gap={0.5} justifyContent="center">
                              <Tooltip title="View Details" arrow>
                                <IconButton
                                  color="primary"
                                  size="small"
                                  onClick={() => handleView(item.id)}
                                  sx={{
                                    '&:hover': {
                                      background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                                      color: 'white',
                                      transform: 'scale(1.1)',
                                    },
                                  }}
                                >
                                  <Visibility fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Delete" arrow>
                                <IconButton
                                  color="error"
                                  size="small"
                                  onClick={() => handleDelete(item.id)}
                                  sx={{
                                    '&:hover': {
                                      bgcolor: 'error.main',
                                      color: 'white',
                                      transform: 'scale(1.1)',
                                    },
                                  }}
                                >
                                  <Delete fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </TableCell>
                        </TableRow>
                      </Fade>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        </Fade>
      </Container>
    </>
  );
}
