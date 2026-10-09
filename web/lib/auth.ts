"use client";

import { useCallback, useEffect, useState } from "react";

import type { AuthUser, Workspace } from "./api/types";

const TOKEN_KEY = "agentguard.token";
const USER_KEY = "agentguard.user";
const WORKSPACE_KEY = "agentguard.workspace";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function getStoredWorkspace(): Workspace | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(WORKSPACE_KEY);
    return raw ? (JSON.parse(raw) as Workspace) : null;
  } catch {
    return null;
  }
}

export function setAuth(token: string, user: AuthUser, workspace: Workspace): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
    window.localStorage.setItem(WORKSPACE_KEY, JSON.stringify(workspace));
  } catch {
    /* storage unavailable — session stays in memory only */
  }
}

export function clearAuth(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
    window.localStorage.removeItem(WORKSPACE_KEY);
  } catch {
    /* ignore */
  }
}

export interface AuthState {
  user: AuthUser | null;
  workspace: Workspace | null;
  ready: boolean;
  isAuthenticated: boolean;
  login: (token: string, user: AuthUser, workspace: Workspace) => void;
  logout: () => void;
}

export function useAuth(): AuthState {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setUser(getStoredUser());
    setWorkspace(getStoredWorkspace());
    setReady(true);
  }, []);

  const login = useCallback(
    (token: string, nextUser: AuthUser, nextWorkspace: Workspace) => {
      setAuth(token, nextUser, nextWorkspace);
      setUser(nextUser);
      setWorkspace(nextWorkspace);
    },
    [],
  );

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
    setWorkspace(null);
  }, []);

  return {
    user,
    workspace,
    ready,
    isAuthenticated: Boolean(user),
    login,
    logout,
  };
}