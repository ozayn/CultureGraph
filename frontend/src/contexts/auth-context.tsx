"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "@/lib/api";
import { GOOGLE_SESSION_ERROR, mapSignInTransportError } from "@/lib/auth-errors";
import { getAuthToken, setAuthToken } from "@/lib/auth-storage";

export interface AuthUser {
  email: string;
  name?: string | null;
  picture?: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  canEdit: boolean;
  googleConfigured: boolean;
  signInLoading: boolean;
  signInError: string | null;
  signInWithGoogleToken: (idToken: string) => Promise<void>;
  clearSignInError: () => void;
  signOut: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
  googleConfigured: boolean;
}

export function AuthProvider({ children, googleConfigured }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [signInLoading, setSignInLoading] = useState(false);
  const [signInError, setSignInError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setUser(null);
      return;
    }

    try {
      const currentUser = await api.get<AuthUser>("/api/auth/me");
      setUser(currentUser);
    } catch {
      setAuthToken(null);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        await refreshUser();
      } finally {
        setLoading(false);
      }
    })();
  }, [refreshUser]);

  const clearSignInError = useCallback(() => {
    setSignInError(null);
  }, []);

  const signInWithGoogleToken = useCallback(async (idToken: string) => {
    setSignInLoading(true);
    setSignInError(null);

    try {
      const response = await api.post<{ access_token: string; user: AuthUser }>(
        "/api/auth/google",
        { id_token: idToken }
      );
      setAuthToken(response.access_token);
      setUser(response.user);
    } catch (error) {
      const detail = mapSignInTransportError(error);
      setSignInError(`${GOOGLE_SESSION_ERROR} ${detail}`);
      throw error;
    } finally {
      setSignInLoading(false);
    }
  }, []);

  const signOut = useCallback(() => {
    setAuthToken(null);
    setUser(null);
    setSignInError(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      canEdit: Boolean(user),
      googleConfigured,
      signInLoading,
      signInError,
      signInWithGoogleToken,
      clearSignInError,
      signOut,
      refreshUser,
    }),
    [
      clearSignInError,
      googleConfigured,
      loading,
      refreshUser,
      signInError,
      signInLoading,
      signInWithGoogleToken,
      signOut,
      user,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
