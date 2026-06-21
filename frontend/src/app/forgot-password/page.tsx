"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PasswordInput } from "@/components/PasswordInput";
import { TopNav } from "@/components/TopNav";
import { api, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [sent, setSent] = useState(false);
  const [devCode, setDevCode] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function sendCode() {
    setError("");
    setMsg("");
    setBusy(true);
    try {
      const res = await api.sendCode({ email, purpose: "password_reset" });
      setSent(true);
      setMsg(`Code emailed. It expires in ${res.expires_in_minutes} minutes.`);
      if (res.dev_code) setDevCode(res.dev_code); // DEV mode convenience
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not send code");
    } finally {
      setBusy(false);
    }
  }

  async function setPassword() {
    setError("");
    if (pw !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await api.resetPassword({ email, code, new_password: pw });
      setMsg("Password updated. Redirecting to login...");
      setTimeout(() => router.push("/login"), 1200);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reset password");
    } finally {
      setBusy(false);
    }
  }

  const codeEntered = code.trim().length >= 4;

  return (
    <div className="min-h-screen bg-white">
      <TopNav variant="navy" />
      <div className="mx-auto max-w-xl px-6 py-16">
        <h1 className="mb-2 text-center text-3xl font-extrabold tracking-wide text-navy">
          RESET PASSWORD
        </h1>
        <p className="mb-10 text-center text-sm text-muted">
          A code is emailed to your address to activate the password fields.
        </p>

        <div className="space-y-5">
          {/* Step 1: email + send code */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="w-44 shrink-0 font-semibold text-navy">
              Email Address
            </label>
            <input
              className="field"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <button
              className="btn-navy shrink-0"
              disabled={busy || !email}
              onClick={sendCode}
            >
              Send Code
            </button>
          </div>

          {sent && (
            <div className="rounded-xl bg-surface p-4 text-sm">
              <p className="text-navy">{msg}</p>
              {devCode && (
                <p className="mt-1 text-muted">
                  Dev mode (no SMTP configured): your code is{" "}
                  <span className="font-mono font-bold text-accent">{devCode}</span>
                </p>
              )}
            </div>
          )}

          {/* Step 2: code */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="w-44 shrink-0 font-semibold text-navy">
              Verification Code
            </label>
            <input
              className="field"
              placeholder="6-digit code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={!sent}
            />
          </div>

          {/* Step 3: new password — activated once a code is entered */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="w-44 shrink-0 font-semibold text-navy">
              New Password
            </label>
            <div className="w-full" style={{ opacity: codeEntered ? 1 : 0.5 }}>
              <PasswordInput
                value={pw}
                onChange={setPw}
                placeholder={codeEntered ? "New password" : "Enter code first"}
              />
            </div>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="w-44 shrink-0 font-semibold text-navy">
              Confirm Password
            </label>
            <div className="w-full" style={{ opacity: codeEntered ? 1 : 0.5 }}>
              <PasswordInput
                value={confirm}
                onChange={setConfirm}
                placeholder="Confirm password"
              />
            </div>
          </div>

          {error && <p className="text-center text-sm text-red-600">{error}</p>}

          <div className="flex justify-center pt-2">
            <button
              className="btn-accent px-10"
              disabled={busy || !codeEntered || !pw}
              onClick={setPassword}
            >
              Set Password
            </button>
          </div>

          <p className="text-center text-sm text-muted">
            <Link href="/login" className="font-semibold text-accent">
              Back to login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
