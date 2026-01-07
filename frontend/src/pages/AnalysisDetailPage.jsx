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
} from '@mui/material';
import { ArrowBack, Download } from '@mui/icons-material';
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
    if (!analysis || !analysis.results_json || !analysis.resultsjson.matches) return;
    
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
        <Container maxWidth="xl" sx={{ mt: 4, textAlign: 'center' }}>
          <CircularProgress />
        </Container>
      </>
    );
  }

  if (error || !analysis) {
    return (
      <>
        <Navbar />
        <Container maxWidth="xl" sx={{ mt: 4 }}>
          <Alert severity="error">{error || 'Analysis not found'}</Alert>
          <Button onClick={() => navigate('/dashboard')} sx={{ mt: 2 }}>
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
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/dashboard')}
          sx={{ mb: 3 }}
        >
          Back to Dashboard
        </Button>

        <Typography variant="h4" fontWeight="bold" gutterBottom>
          📄 Analysis Details
        </Typography>
        <Typography variant="body1" color="text.secondary" gutterBottom>
          {analysis.rfp_filename}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Analyzed on {new Date(analysis.created_at).toLocaleString()}
        </Typography>

        {/* Statistics */}
        <Grid container spacing={2} sx={{ mb: 4 }}>
          <Grid item xs={6} sm={2}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h5" fontWeight="bold">{analysis.num_required_docs}</Typography>
                <Typography variant="body2" color="text.secondary">Required</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={2}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h5" fontWeight="bold">{analysis.num_provided_docs}</Typography>
                <Typography variant="body2" color="text.secondary">Provided</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={2}>
            <Card sx={{ bgcolor: 'success.light' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h5" fontWeight="bold">{analysis.num_matched}</Typography>
                <Typography variant="body2">✅ Matched</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={2}>
            <Card sx={{ bgcolor: 'warning.light' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h5" fontWeight="bold">{analysis.num_review}</Typography>
                <Typography variant="body2">⚠️ Review</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={2}>
            <Card sx={{ bgcolor: 'error.light' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h5" fontWeight="bold">{analysis.num_missing}</Typography>
                <Typography variant="body2">❌ Missing</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={2}>
            <Card sx={{ bgcolor: 'info.light' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h5" fontWeight="bold">
                  {analysis.completion_rate.toFixed(0)}%
                </Typography>
                <Typography variant="body2">Complete</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Results Table */}
        {analysis.results_json && (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell width="25%"><strong>Required Document</strong></TableCell>
                  <TableCell width="30%"><strong>Description</strong></TableCell>
                  <TableCell width="15%"><strong>Status</strong></TableCell>
                  <TableCell width="20%"><strong>Matched File</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {analysis.results_json.matches.map((match, idx) => (
                  <TableRow key={idx}>
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
                      <Chip label={match.status} color={getStatusColor(match.status)} size="small" />
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
        )}

        <Box sx={{ mt: 4, display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button
            variant="contained"
            startIcon={<Download />}
            onClick={downloadCSV}
          >
            Download CSV
          </Button>
          <Button
            variant="outlined"
            onClick={() => navigate('/dashboard')}
          >
            Back to Dashboard
          </Button>
        </Box>

        {analysis.api_cost > 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 3, textAlign: 'center' }}>
            💰 API Cost: ${analysis.api_cost.toFixed(4)}
          </Typography>
        )}
      </Container>
    </>
  );
}
