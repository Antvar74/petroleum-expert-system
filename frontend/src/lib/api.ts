/**
 * Centralized Axios instance with JWT interceptor.
 *
 * Every component should import `api` from here instead of using `axios` directly
 * for requests that need authentication.  The interceptor automatically attaches
 * the Authorization header from localStorage.
 */
import axios from 'axios';
import { API_BASE_URL } from '../config';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// --- Request interceptor: attach JWT ---
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('petroexpert-token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Response interceptor: handle 401 globally ---
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid — clear auth state
      localStorage.removeItem('petroexpert-token');
      localStorage.removeItem('petroexpert-user');
      // Dispatch a custom event so AuthContext can react
      window.dispatchEvent(new Event('petroexpert-logout'));
    }
    return Promise.reject(error);
  },
);

export default api;
