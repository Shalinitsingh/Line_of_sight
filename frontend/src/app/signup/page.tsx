"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { GoogleSignInButton } from "@/components/GoogleSignInButton";
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
          <GoogleSignInButton label="Sign up with Google" />

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
