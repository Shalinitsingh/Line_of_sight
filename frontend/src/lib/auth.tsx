"use client";

import { useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";

import { AuthResult } from "./api";

interface Session {
  token: string;
  industry?: string;
  fullName?: string | null;
}

interface AuthCtx {
  session: Session | null;
  ready: boolean;
  signIn: (r: AuthResult) => void;
  signOut: () => void;
}

const Ctx = createContext<AuthCtx>({
  session: null,
  ready: false,
  signIn: () => {},
  signOut: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = window.localStorage.getItem("los_token");
    if (token) {
      setSession({
        token,
        industry: window.localStorage.getItem("los_industry") || undefined,
        fullName: window.localStorage.getItem("los_name"),
      });
    }
    setReady(true);
  }, []);

  const signIn = (r: AuthResult) => {
    window.localStorage.setItem("los_token", r.token);
    if (r.industry) window.localStorage.setItem("los_industry", r.industry);
    if (r.full_name) window.localStorage.setItem("los_name", r.full_name);
    setSession({ token: r.token, industry: r.industry, fullName: r.full_name });
  };

  const signOut = () => {
    window.localStorage.removeItem("los_token");
    window.localStorage.removeItem("los_name");
    setSession(null);
  };

  return (
    <Ctx.Provider value={{ session, ready, signIn, signOut }}>{children}</Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);

/** Redirect to /login if there's no session. Use inside app pages. */
export function useRequireAuth() {
  const { session, ready } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (ready && !session) router.replace("/login");
  }, [ready, session, router]);
  return session;
}
