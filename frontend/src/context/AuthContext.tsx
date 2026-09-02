"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { getAccessToken, setAccessToken } from "@/services/api/client";
import type { CurrentUser } from "@/services/api/types";
import * as authService from "@/services/auth";

export type AuthStatus = "loading" | "authenticated" | "anonymous";

export interface SignUpOutcome {
  /** True when Supabase requires the address to be confirmed before a session is issued. */
  emailConfirmationRequired: boolean;
}

interface AuthContextValue {
  status: AuthStatus;
  user: CurrentUser | null;
  signUp: (email: string, password: string) => Promise<SignUpOutcome>;
  logIn: (email: string, password: string) => Promise<void>;
  logOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    let cancelled = false;

    if (!getAccessToken()) {
      setStatus("anonymous");
      return;
    }

    authService
      .getCurrentUser()
      .then((currentUser) => {
        if (!cancelled) {
          setUser(currentUser);
          setStatus("authenticated");
        }
      })
      .catch(() => {
        if (!cancelled) {
          // The stored token is expired or invalid; start clean.
          setAccessToken(null);
          setUser(null);
          setStatus("anonymous");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const signUp = useCallback(async (email: string, password: string): Promise<SignUpOutcome> => {
    const result = await authService.signUp(email, password);
    if (!result.session) {
      return { emailConfirmationRequired: true };
    }
    setAccessToken(result.session.access_token);
    setUser({ id: result.session.user_id, email: result.session.email });
    setStatus("authenticated");
    return { emailConfirmationRequired: false };
  }, []);

  const logIn = useCallback(async (email: string, password: string): Promise<void> => {
    const session = await authService.logIn(email, password);
    setAccessToken(session.access_token);
    setUser({ id: session.user_id, email: session.email });
    setStatus("authenticated");
  }, []);

  const logOut = useCallback(async (): Promise<void> => {
    try {
      await authService.logOut();
    } catch {
      // Signing out locally must succeed even if the server call fails.
    }
    setAccessToken(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, signUp, logIn, logOut }),
    [status, user, signUp, logIn, logOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
