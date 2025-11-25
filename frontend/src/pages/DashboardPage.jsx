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
} from '@mui/material';
import {
  Add,
  Visibility,
  Delete,
  Assessment,
  CheckCircle,
  Warning,
  Cancel,
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
        <Container maxWidth="xl" sx={{ mt: 4, textAlign: 'center' }}>
          <CircularProgress />
        </Container>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Box>
            <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
              📊 Dashboard
            </Typography>
            <Typography variant="body1" color="text.secondary">
              View and manage your RFP compliance analyses
            </Typography>
          </Box>
          <Button
            variant="contained"
            size="large"
            startIcon={<Add />}
            onClick={() => navigate('/analyze')}
          >
            New Analysis
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {/* Statistics Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Assessment sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
                  <Box>
                    <Typography variant="h4" fontWeight="bold">
                      {stats.totalAnalyses}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Analyses
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <CheckCircle sx={{ fontSize: 40, color: 'success.main', mr: 2 }} />
                  <Box>
                    <Typography variant="h4" fontWeight="bold">
                      {stats.avgCompletionRate.toFixed(1)}%
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Avg Completion Rate
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Typography variant="h4" sx={{ fontSize: 40, mr: 2 }}>
                    💰
                  </Typography>
                  <Box>
                    <Typography variant="h4" fontWeight="bold">
                      ${stats.totalCost.toFixed(2)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total API Cost
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Analysis History Table */}
        <Paper sx={{ borderRadius: 2 }}>
          <Box sx={{ p: 3, borderBottom: '1px solid', borderColor: 'divider' }}>
            <Typography variant="h6" fontWeight="bold">
              Analysis History
            </Typography>
          </Box>
          {history.length === 0 ? (
            <Box sx={{ p: 6, textAlign: 'center' }}>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No analyses yet
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
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
                    <TableCell><strong>RFP Document</strong></TableCell>
                    <TableCell align="center"><strong>Date</strong></TableCell>
                    <TableCell align="center"><strong>Required Docs</strong></TableCell>
                    <TableCell align="center"><strong>Provided Docs</strong></TableCell>
                    <TableCell align="center"><strong>Matched</strong></TableCell>
                    <TableCell align="center"><strong>Review</strong></TableCell>
                    <TableCell align="center"><strong>Missing</strong></TableCell>
                    <TableCell align="center"><strong>Completion</strong></TableCell>
                    <TableCell align="center"><strong>Cost</strong></TableCell>
                    <TableCell align="center"><strong>Actions</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {history.map((item) => (
                    <TableRow key={item.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {item.rfp_filename}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color="text.secondary">
                          {formatDate(item.created_at)}
                        </Typography>
                      </TableCell>
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
                      <TableCell align="center">
                        <Typography variant="body2">
                          ${item.api_cost.toFixed(4)}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => handleView(item.id)}
                        >
                          <Visibility />
                        </IconButton>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDelete(item.id)}
                        >
                          <Delete />
                        </IconButton>
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
