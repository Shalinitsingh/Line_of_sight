"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Brand } from "@/components/Brand";
import { GoogleSignInButton } from "@/components/GoogleSignInButton";
import { IndustryToggle } from "@/components/IndustryToggle";
import { PasswordInput } from "@/components/PasswordInput";
import { TopNav } from "@/components/TopNav";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError("");
    setBusy(true);
    try {
      const res = await api.login({ email, password });
      signIn(res);
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-white">
      <TopNav variant="blue" />
      <div className="mx-auto grid max-w-6xl gap-10 px-6 py-16 md:grid-cols-[1fr_1.1fr_auto]">
        <Brand />

        <div className="mx-auto w-full max-w-sm">
          <h1 className="mb-8 text-center text-3xl font-extrabold tracking-wide text-navy">
            LOG IN
          </h1>
          <div className="space-y-4">
            <input
              className="field"
              placeholder="Email Address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
            <PasswordInput value={password} onChange={setPassword} />

            {error && <p className="text-center text-sm text-red-600">{error}</p>}

            <p className="pt-2 text-center text-sm text-muted">New here?</p>
            <div className="flex justify-center gap-4">
              <button className="btn-navy" disabled={busy} onClick={submit}>
                {busy ? "..." : "Sign In"}
              </button>
              <Link href="/signup" className="btn-accent inline-block">
                Sign Up
              </Link>
            </div>

            <div className="pt-4 text-center">
              <p className="text-sm text-muted">Can&apos;t remember your password?</p>
              <Link
                href="/forgot-password"
                className="btn-accent mt-2 inline-block px-8"
              >
                Help
              </Link>
            </div>

            <p className="pt-2 text-center text-sm text-muted">or</p>
            <GoogleSignInButton />

            <div className="pt-6 text-center">
              <Link
                href="/about"
                className="btn-accent inline-block bg-accent px-8 py-3 text-center text-sm leading-tight"
              >
                Help us Improve
                <br />
                Share your Feedback
              </Link>
            </div>
          </div>
        </div>

        <div className="hidden md:block">
          <IndustryToggle />
        </div>
      </div>
    </div>
  );
}
