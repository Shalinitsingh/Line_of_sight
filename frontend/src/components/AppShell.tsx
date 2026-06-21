"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAuth, useRequireAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";

const TABS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/datasets", label: "Data Ingestion" },
  { href: "/ai-tracker", label: "AI Tracker" },
  { href: "/reports", label: "Reports" },
  { href: "/about", label: "About" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const session = useRequireAuth();
  const { signOut } = useAuth();
  const { industry } = useTheme();
  const pathname = usePathname();
  const router = useRouter();

  if (!session) return null; // redirecting to /login

  return (
    <div className="min-h-screen bg-surface">
      <header className="bg-navy text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link href="/dashboard" className="text-lg font-extrabold">
            Line<span className="text-accent">·</span>of
            <span className="text-accent">·</span>Sight
          </Link>
          <nav className="hidden gap-6 text-sm font-medium md:flex">
            {TABS.map((t) => {
              const active = pathname === t.href;
              return (
                <Link
                  key={t.href}
                  href={t.href}
                  className={active ? "text-accent" : "opacity-80 hover:opacity-100"}
                >
                  {t.label}
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-4">
            <span className="hidden rounded-full bg-white/10 px-3 py-1 text-xs capitalize sm:inline">
              {industry}
            </span>
            <button
              onClick={() => {
                signOut();
                router.push("/login");
              }}
              className="text-sm opacity-80 hover:opacity-100"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
    </div>
  );
}

export function Card({
  title,
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-line bg-white p-6 shadow-card">
      {title && <h3 className="mb-4 text-lg font-bold text-navy">{title}</h3>}
      {children}
    </section>
  );
}
