"use client";

import { createContext, useContext } from "react";

export type IdentityProvider = "google" | "microsoft" | "facebook";

export interface AuthUser {
  email: string;
  name: string;
}

export interface SignInOptions {
  /** Dev provider only: email used for the fake user. */
  devEmail?: string;
}

export interface AuthContextValue {
  user: AuthUser | null;
  /** Access token for the API, or null when signed out. */
  token: string | null;
  /** True until the initial auth state is known. */
  loading: boolean;
  mode: "dev" | "entra";
  signIn: (provider: IdentityProvider, options?: SignInOptions) => Promise<void>;
  signOut: () => Promise<void>;
  /** Returns a fresh token (refreshing silently when needed). */
  getToken: () => Promise<string | null>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

export const PROVIDER_LABELS: Record<IdentityProvider, string> = {
  google: "Google",
  microsoft: "Microsoft",
  facebook: "Facebook",
};

const RETURN_KEY = "aussold.returnTo";

/** Only same-site relative paths are allowed as post-login targets. */
export function safePath(p: string | null | undefined): string | null {
  return p && p.startsWith("/") && !p.startsWith("//") && !p.includes("\\") ? p : null;
}

export function setReturnTo(path: string | null | undefined): void {
  const safe = safePath(path);
  if (safe) sessionStorage.setItem(RETURN_KEY, safe);
}

export function consumeReturnTo(): string | null {
  const v = safePath(sessionStorage.getItem(RETURN_KEY));
  sessionStorage.removeItem(RETURN_KEY);
  return v;
}
