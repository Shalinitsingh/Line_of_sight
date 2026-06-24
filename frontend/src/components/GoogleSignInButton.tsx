"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";

// Minimal typing for the Google Identity Services global.
interface GoogleId {
  accounts: {
    id: {
      initialize: (cfg: {
        client_id: string;
        callback: (resp: { credential: string }) => void;
      }) => void;
      renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void;
    };
  };
}
declare global {
  interface Window {
    google?: GoogleId;
  }
}

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

export function GoogleSignInButton({
  label = "Sign in with Google",
}: {
  label?: string;
}) {
  const router = useRouter();
  const { signIn } = useAuth();
  const { industry } = useTheme();
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!CLIENT_ID || !ref.current) return;

    async function handle(resp: { credential: string }) {
      try {
        const res = await api.googleSignin({ credential: resp.credential, industry });
        signIn(res);
        router.push("/dashboard");
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Google sign-in failed");
      }
    }

    function init() {
      if (!window.google || !ref.current) return;
      window.google.accounts.id.initialize({ client_id: CLIENT_ID!, callback: handle });
      window.google.accounts.id.renderButton(ref.current, {
        theme: "outline",
        size: "large",
        shape: "pill",
        text: "continue_with",
      });
    }

    if (window.google) {
      init();
    } else {
      const s = document.createElement("script");
      s.src = "https://accounts.google.com/gsi/client";
      s.async = true;
      s.onload = init;
      document.body.appendChild(s);
    }
  }, [industry, router, signIn]);

  if (!CLIENT_ID) {
    return (
      <p className="text-center text-xs text-muted">
        Google sign-in is available once <code>NEXT_PUBLIC_GOOGLE_CLIENT_ID</code> is
        set (see README).
      </p>
    );
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <div ref={ref} aria-label={label} />
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
