"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { AccountInfo, PublicClientApplication } from "@azure/msal-browser";
import { ENTRA, IDP_DOMAIN_HINTS } from "../config";
import { AuthContext, type AuthContextValue, type AuthUser } from "./context";

let appPromise: Promise<PublicClientApplication> | null = null;

function getApp(): Promise<PublicClientApplication> {
  appPromise ??= import("@azure/msal-browser").then(async ({ PublicClientApplication }) => {
    const app = new PublicClientApplication({
      auth: {
        clientId: ENTRA.clientId,
        authority: ENTRA.authority,
        knownAuthorities: [new URL(ENTRA.authority).host],
        redirectUri: `${window.location.origin}/login`,
        postLogoutRedirectUri: window.location.origin,
      },
      cache: { cacheLocation: "sessionStorage" },
    });
    await app.initialize();
    return app;
  });
  return appPromise;
}

function toUser(account: AccountInfo): AuthUser {
  const claims = account.idTokenClaims as { email?: string; emails?: string[] } | undefined;
  const email = claims?.email ?? claims?.emails?.[0] ?? account.username;
  return { email, name: account.name || email };
}

/** Production auth via Microsoft Entra External ID (MSAL redirect flow). */
export function EntraAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const accountRef = useRef<AccountInfo | null>(null);

  const acquire = useCallback(async (account: AccountInfo): Promise<string | null> => {
    const app = await getApp();
    try {
      const res = await app.acquireTokenSilent({ scopes: [ENTRA.apiScope], account });
      return res.accessToken;
    } catch {
      await app.acquireTokenRedirect({ scopes: [ENTRA.apiScope], account });
      return null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const app = await getApp();
        const result = await app.handleRedirectPromise();
        const account = result?.account ?? app.getActiveAccount() ?? app.getAllAccounts()[0] ?? null;
        if (!account) return;
        app.setActiveAccount(account);
        accountRef.current = account;
        const accessToken = result?.accessToken ?? (await acquire(account));
        if (cancelled) return;
        setUser(toUser(account));
        setToken(accessToken);
      } catch {
        if (!cancelled) {
          setUser(null);
          setToken(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [acquire]);

  const signIn = useCallback<AuthContextValue["signIn"]>(async (provider) => {
    const app = await getApp();
    await app.loginRedirect({
      scopes: [ENTRA.apiScope],
      extraQueryParameters: { domain_hint: IDP_DOMAIN_HINTS[provider] },
    });
  }, []);

  const signOut = useCallback(async () => {
    const app = await getApp();
    setUser(null);
    setToken(null);
    await app.logoutRedirect({ account: accountRef.current ?? undefined });
  }, []);

  const getToken = useCallback(async () => {
    if (!accountRef.current) return null;
    const fresh = await acquire(accountRef.current);
    setToken(fresh);
    return fresh;
  }, [acquire]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, token, loading, mode: "entra", signIn, signOut, getToken }),
    [user, token, loading, signIn, signOut, getToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
