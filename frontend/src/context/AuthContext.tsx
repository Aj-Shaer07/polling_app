import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { api, ApiError } from '../api/client';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (u: string, p: string) => Promise<void>;
  studentActivate: (id: string, p: string) => Promise<void>;
  studentLogin: (id: string, p: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const me = await api.getMe();
      setUser(me);
    } catch {
      setUser(null);
      localStorage.removeItem('bst_token');
    } finally {
      setLoading(false);
    }
  };

  const broadcastAuthEvent = (type: 'LOGIN' | 'LOGOUT' | 'REFRESH') => {
    try {
      if (typeof BroadcastChannel !== 'undefined') {
        const channel = new BroadcastChannel('bst_auth_sync');
        channel.postMessage({ type, timestamp: Date.now() });
        channel.close();
      }
    } catch {
      // BroadcastChannel unavailable
    }
  };

  useEffect(() => {
    refreshUser();

    // 1. Cross-tab sync via BroadcastChannel
    let channel: BroadcastChannel | null = null;
    try {
      if (typeof BroadcastChannel !== 'undefined') {
        channel = new BroadcastChannel('bst_auth_sync');
        channel.onmessage = (event) => {
          if (event.data?.type === 'LOGOUT') {
            setUser(null);
            localStorage.removeItem('bst_token');
          } else if (event.data?.type === 'LOGIN' || event.data?.type === 'REFRESH') {
            refreshUser();
          }
        };
      }
    } catch (err) {
      console.warn('BroadcastChannel error:', err);
    }

    // 2. Cross-tab sync fallback via StorageEvent
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'bst_token') {
        if (!e.newValue) {
          // Token removed in another tab -> logout immediately
          setUser(null);
        } else {
          // Token updated in another tab -> refresh user identity immediately
          refreshUser();
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      channel?.close();
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const login = async (u: string, p: string) => {
    const res = await api.login(u, p);
    if (res.access_token) {
      localStorage.setItem('bst_token', res.access_token);
    }
    await refreshUser();
    broadcastAuthEvent('LOGIN');
  };

  const studentActivate = async (id: string, p: string) => {
    const res = await api.studentActivate(id, p);
    if (res.access_token) {
      localStorage.setItem('bst_token', res.access_token);
    }
    await refreshUser();
    broadcastAuthEvent('LOGIN');
  };

  const studentLogin = async (id: string, p: string) => {
    const res = await api.studentLogin(id, p);
    if (res.access_token) {
      localStorage.setItem('bst_token', res.access_token);
    }
    await refreshUser();
    broadcastAuthEvent('LOGIN');
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch {
      // ignore
    } finally {
      localStorage.removeItem('bst_token');
      setUser(null);
      broadcastAuthEvent('LOGOUT');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        studentActivate,
        studentLogin,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
