"use client";

import { useCallback, useMemo, useSyncExternalStore, type ReactNode } from "react";
import { AuthContext, PROVIDER_LABELS, type AuthContextValue, type AuthUser } from "./context";

const KEY = "aussold.dev-user";
const SERVER = "__server__";
const listeners = new Set<() => void>();

function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
}

const getSnapshot = () => localStorage.getItem(KEY) ?? "";
const getServerSnapshot = () => SERVER;

function parse(raw: string): AuthUser | null {
  if (!raw || raw === SERVER) return null;
  try {
    const u = JSON.parse(raw) as Partial<AuthUser>;
    return typeof u.email === "string" && typeof u.name === "string" ? { email: u.email, name: u.name } : null;
  } catch {
    return null;
  }
}

/** Dev/mock auth: a fake user in localStorage, token `dev:<email>`. Not for production. */
export function DevAuthProvider({ children }: { children: ReactNode }) {
  const raw = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const user = useMemo(() => parse(raw), [raw]);
  const token = user ? `dev:${user.email}` : null;

  const signIn = useCallback<AuthContextValue["signIn"]>(async (provider, options) => {
    const email = (options?.devEmail?.trim() || `dev.${provider}@example.com`).toLowerCase();
    const next: AuthUser = { email, name: `Dev User (${PROVIDER_LABELS[provider]})` };
    localStorage.setItem(KEY, JSON.stringify(next));
    listeners.forEach((l) => l());
  }, []);

  const signOut = useCallback(async () => {
    localStorage.removeItem(KEY);
    listeners.forEach((l) => l());
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      loading: raw === SERVER,
      mode: "dev",
      signIn,
      signOut,
      getToken: async () => token,
    }),
    [user, token, raw, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
