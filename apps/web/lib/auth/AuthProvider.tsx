"use client";

import type { ReactNode } from "react";
import { USE_DEV_AUTH } from "../config";
import { DevAuthProvider } from "./dev";
import { EntraAuthProvider } from "./entra";

/** Picks the auth implementation from env; both expose the same `useAuth()` interface. */
export function AuthProvider({ children }: { children: ReactNode }) {
  return USE_DEV_AUTH ? (
    <DevAuthProvider>{children}</DevAuthProvider>
  ) : (
    <EntraAuthProvider>{children}</EntraAuthProvider>
  );
}
