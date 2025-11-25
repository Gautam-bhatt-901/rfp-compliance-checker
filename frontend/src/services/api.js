/**
 * API client for backend communication
 * Handles authentication, file uploads, and RFP analysis
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Authentication API
export const authAPI = {
  register: async (email, password, fullName) => {
    const response = await api.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    return response.data;
  },
  
  login: async (email, password) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await axios.post(`${API_BASE_URL}/auth/login`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  
  getMe: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

// RFP Analysis API
export const rfpAPI = {
  analyzeCompliance: async (rfpFile, providedFiles, onProgress) => {
    const formData = new FormData();
    formData.append('rfp_file', rfpFile);
    
    providedFiles.forEach((file) => {
      formData.append('provided_files', file);
    });
    
    const response = await api.post('/rfp/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress?.(progress);
      },
    });
    return response.data;
  },
  
  // NEW: History endpoints
  getHistory: async () => {
    const response = await api.get('/rfp/history');
    return response.data;
  },
  
  getAnalysisDetail: async (id) => {
    const response = await api.get(`/rfp/history/${id}`);
    return response.data;
  },
  
  deleteAnalysis: async (id) => {
    const response = await api.delete(`/rfp/history/${id}`);
    return response.data;
  },
};

// Health check API
export const healthAPI = {
  check: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
