/**
 * Authentication context for PETROEXPERT.
 *
 * Provides user state, login/register/logout actions, and a loading guard.
 * Follows the same Context + Provider pattern as ToastProvider.
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface AuthUser {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (login: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------
const AuthContext = createContext<AuthContextValue | null>(null);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------
const TOKEN_KEY = 'petroexpert-token';
const USER_KEY = 'petroexpert-user';

function persistAuth(token: string, user: AuthUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

function loadPersistedAuth(): { token: string | null; user: AuthUser | null } {
  const token = localStorage.getItem(TOKEN_KEY);
  const raw = localStorage.getItem(USER_KEY);
  if (token && raw) {
    // Client-side expiry check — reject expired tokens immediately
    if (isTokenExpired(token)) {
      clearAuth();
      return { token: null, user: null };
    }
    try {
      return { token, user: JSON.parse(raw) };
    } catch {
      clearAuth();
    }
  }
  return { token: null, user: null };
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session on mount
  useEffect(() => {
    const saved = loadPersistedAuth();
    if (saved.token && saved.user) {
      setToken(saved.token);
      setUser(saved.user);
      // Validate the token is still valid via the centralized api client
      api
        .get(`/auth/me`, {
          headers: { Authorization: `Bearer ${saved.token}` },
        })
        .then((res) => {
          setUser(res.data);
          persistAuth(saved.token!, res.data);
        })
        .catch(() => {
          // Token expired — clear
          clearAuth();
          setToken(null);
          setUser(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  // Listen for forced logout from axios interceptor
  useEffect(() => {
    const handler = () => {
      clearAuth();
      setToken(null);
      setUser(null);
    };
    window.addEventListener('petroexpert-logout', handler);
    return () => window.removeEventListener('petroexpert-logout', handler);
  }, []);

  const login = useCallback(async (loginStr: string, password: string) => {
    const res = await api.post(`/auth/login`, {
      login: loginStr,
      password,
    });
    const { access_token, user: userData } = res.data;
    persistAuth(access_token, userData);
    setToken(access_token);
    setUser(userData);
  }, []);

  const register = useCallback(async (username: string, email: string, password: string, fullName?: string) => {
    const res = await api.post(`/auth/register`, {
      username,
      email,
      password,
      full_name: fullName || null,
    });
    const { access_token, user: userData } = res.data;
    persistAuth(access_token, userData);
    setToken(access_token);
    setUser(userData);
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
