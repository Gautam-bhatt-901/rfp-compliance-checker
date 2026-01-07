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
} from '@mui/material';
import {
  Add,
  Visibility,
  Delete,
  Assessment,
  CheckCircle,
  Warning,
  Cancel,
  FolderOpen,
  Search,
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
  
  //  Search and sorting state
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('created_at'); // 'created_at' or 'completion_rate'
  const [sortOrder, setSortOrder] = useState('desc'); // 'asc' or 'desc'

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const data = await rfpAPI.getHistory();
      setHistory(data);

      // Calculate stats
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

  //  Handle sort request
  const handleSort = (column) => {
    if (sortBy === column) {
      // Toggle sort order if clicking same column
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      // Set new column and default to descending
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  //  Filter and sort history
  const getFilteredAndSortedHistory = () => {
    // Filter by search query
    let filtered = history.filter((item) => {
      const searchLower = searchQuery.toLowerCase();
      return (
        item.rfp_filename.toLowerCase().includes(searchLower) ||
        formatDate(item.created_at).toLowerCase().includes(searchLower) ||
        item.completion_rate.toString().includes(searchLower)
      );
    });

    // Sort the filtered results
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
          <CircularProgress size={60} />
        </Container>
      </>
    );
  }

  // Get filtered and sorted data
  const displayHistory = getFilteredAndSortedHistory();

  return (
    <>
      <Navbar />
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Box>
            <Typography variant="h4" fontWeight="bold" gutterBottom>
              📊 Dashboard
            </Typography>
            <Typography variant="body1" color="text.secondary">
              View and manage your RFP compliance analyses
            </Typography>
          </Box>
          <Button
            variant="contained"
            color="primary"
            startIcon={<Add />}
            onClick={() => navigate('/analyze')}
            size="large"
          >
            New Analysis
          </Button>
        </Box>

        {error && (
          <Alert severity="error" onClose={() => setError('')} sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Statistics Cards */}
        <Grid container spacing={3} mb={4}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <Assessment color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6" color="text.secondary">
                    Total Analyses
                  </Typography>
                </Box>
                <Typography variant="h4" fontWeight="bold">
                  {stats.totalAnalyses}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <CheckCircle color="success" sx={{ mr: 1 }} />
                  <Typography variant="h6" color="text.secondary">
                    Avg Completion Rate
                  </Typography>
                </Box>
                <Typography variant="h4" fontWeight="bold">
                  {stats.avgCompletionRate.toFixed(1)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <Warning color="warning" sx={{ mr: 1 }} />
                  <Typography variant="h6" color="text.secondary">
                    Total API Cost
                  </Typography>
                </Box>
                <Typography variant="h4" fontWeight="bold">
                  ${stats.totalCost.toFixed(2)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Analysis History Table */}
        <Paper sx={{ p: 3 }}>
          {/*  Header with search */}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Typography variant="h5" fontWeight="bold">
              Analysis History
            </Typography>
            {/*  Search field */}
            <TextField
              placeholder="Search analyses..."
              variant="outlined"
              size="small"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              sx={{ width: 300 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
            />
          </Box>

          {history.length === 0 ? (
            <Box textAlign="center" py={8}>
              <Assessment sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No analyses yet
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={3}>
                Start by uploading your first RFP document
              </Typography>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => navigate('/analyze')}
              >
                Create First Analysis
              </Button>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    {/*  Batch column */}
                    <TableCell><strong>RFP Document</strong></TableCell>
                    {/*  Date with sorting */}
                    <TableCell>
                      <TableSortLabel
                        active={sortBy === 'created_at'}
                        direction={sortBy === 'created_at' ? sortOrder : 'desc'}
                        onClick={() => handleSort('created_at')}
                      >
                        <strong>Date</strong>
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="center"><strong>Required Docs</strong></TableCell>
                    <TableCell align="center"><strong>Provided Docs</strong></TableCell>
                    <TableCell align="center"><strong>Matched</strong></TableCell>
                    <TableCell align="center"><strong>Review</strong></TableCell>
                    <TableCell align="center"><strong>Missing</strong></TableCell>
                    {/*  Completion with sorting */}
                    <TableCell align="center">
                      <TableSortLabel
                        active={sortBy === 'completion_rate'}
                        direction={sortBy === 'completion_rate' ? sortOrder : 'desc'}
                        onClick={() => handleSort('completion_rate')}
                      >
                        <strong>Completion</strong>
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="center"><strong>Cost</strong></TableCell>
                    <TableCell align="center"><strong>Actions</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {displayHistory.map((item) => (
                    <TableRow key={item.id} hover>
                      {/*  Batch column cell */}
                      <TableCell>{item.rfp_filename}</TableCell>
                      <TableCell>{formatDate(item.created_at)}</TableCell>
                      <TableCell align="center">{item.num_required_docs}</TableCell>
                      <TableCell align="center">{item.num_provided_docs}</TableCell>
                      <TableCell align="center">
                        <Chip
                          icon={<CheckCircle />}
                          label={item.num_matched}
                          color="success"
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          icon={<Warning />}
                          label={item.num_review}
                          color="warning"
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          icon={<Cancel />}
                          label={item.num_missing}
                          color="error"
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={`${item.completion_rate.toFixed(1)}%`}
                          color={getCompletionColor(item.completion_rate)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">${item.api_cost.toFixed(4)}</TableCell>
                      <TableCell align="center">
                        <Tooltip title="View Details">
                          <IconButton
                            color="primary"
                            size="small"
                            onClick={() => handleView(item.id)}
                          >
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete">
                          <IconButton
                            color="error"
                            size="small"
                            onClick={() => handleDelete(item.id)}
                          >
                            <Delete />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      </Container>
    </>
  );
}
