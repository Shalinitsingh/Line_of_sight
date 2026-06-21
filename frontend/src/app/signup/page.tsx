"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { IndustryToggle } from "@/components/IndustryToggle";
import { PasswordInput } from "@/components/PasswordInput";
import { TopNav } from "@/components/TopNav";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";

export default function SignupPage() {
  const router = useRouter();
  const { signIn } = useAuth();
  const { industry } = useTheme();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    setBusy(true);
    try {
      const res = await api.signup({
        full_name: fullName,
        email,
        password,
        industry,
      });
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
      <div className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-16 md:grid-cols-2">
        <div>
          <h1 className="mb-10 text-center text-3xl font-extrabold tracking-wide text-navy md:text-left">
            SIGN UP
          </h1>
          <h2 className="text-5xl font-extrabold leading-tight text-navy">
            We are Glad
            <br />
            you are here
          </h2>
          <div className="mt-8 md:hidden">
            <IndustryToggle />
          </div>
        </div>

        <div className="mx-auto w-full max-w-sm space-y-4">
          <input
            className="field"
            placeholder="Full Name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <input
            className="field"
            placeholder="Email Address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <PasswordInput value={password} onChange={setPassword} />
          <PasswordInput
            value={confirm}
            onChange={setConfirm}
            placeholder="Confirm Password"
          />

          {error && <p className="text-center text-sm text-red-600">{error}</p>}

          <div className="flex justify-center pt-2">
            <button className="btn-accent px-10" disabled={busy} onClick={submit}>
              {busy ? "..." : "Sign Up"}
            </button>
          </div>

          <p className="text-center text-sm text-muted">or</p>
          <button
            type="button"
            disabled
            title="Google sign-in is not wired in this build"
            className="mx-auto flex cursor-not-allowed items-center justify-center gap-2 text-sm font-medium text-navy opacity-70"
          >
            <GoogleMark /> Sign up with Google
          </button>

          <p className="pt-2 text-center text-sm text-muted">
            Already have an account?{" "}
            <Link href="/login" className="font-semibold text-accent">
              Log in
            </Link>
          </p>

          <div className="hidden justify-center pt-4 md:flex">
            <IndustryToggle />
          </div>
        </div>
      </div>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48">
      <path
        fill="#EA4335"
        d="M24 9.5c3.5 0 6.6 1.2 9 3.6l6.7-6.7C35.6 2.7 30.2 0 24 0 14.6 0 6.4 5.4 2.6 13.2l7.8 6.1C12.2 13.3 17.6 9.5 24 9.5Z"
      />
      <path
        fill="#4285F4"
        d="M46.1 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.4c-.5 2.9-2.2 5.3-4.7 7l7.2 5.6c4.2-3.9 6.6-9.6 6.6-17.1Z"
      />
      <path
        fill="#FBBC05"
        d="M10.4 28.3c-.5-1.5-.8-3-.8-4.6s.3-3.1.8-4.6l-7.8-6.1C1 16.1 0 19.9 0 23.7s1 7.6 2.6 10.7l7.8-6.1Z"
      />
      <path
        fill="#34A853"
        d="M24 48c6.5 0 11.9-2.1 15.8-5.8l-7.2-5.6c-2 1.4-4.6 2.2-8.6 2.2-6.4 0-11.8-3.8-13.6-9.3l-7.8 6.1C6.4 42.6 14.6 48 24 48Z"
      />
    </svg>
  );
}
