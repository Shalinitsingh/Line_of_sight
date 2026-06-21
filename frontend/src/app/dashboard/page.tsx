"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell, Card } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function DashboardPage() {
  const { session } = useAuth();
  const [datasets, setDatasets] = useState(0);
  const [reports, setReports] = useState(0);
  const [audit, setAudit] = useState<{ action: string; created_at: string }[]>([]);

  useEffect(() => {
    api
      .listDatasets()
      .then((d) => setDatasets(d.length))
      .catch(() => {});
    api
      .listReports()
      .then((r) => setReports(r.length))
      .catch(() => {});
    api
      .audit()
      .then((a) => setAudit(a.slice(0, 8)))
      .catch(() => {});
  }, []);

  return (
    <AppShell>
      <h1 className="mb-1 text-3xl font-extrabold text-navy">
        Welcome{session?.fullName ? `, ${session.fullName}` : ""}
      </h1>
      <p className="mb-8 text-muted">Create Insights in 5 Easy Steps.</p>

      <div className="mb-8 grid gap-6 sm:grid-cols-3">
        <Card>
          <p className="text-sm text-muted">Datasets</p>
          <p className="text-4xl font-extrabold text-navy">{datasets}</p>
          <Link href="/datasets" className="text-sm font-semibold text-accent">
            Ingest data →
          </Link>
        </Card>
        <Card>
          <p className="text-sm text-muted">Reports</p>
          <p className="text-4xl font-extrabold text-navy">{reports}</p>
          <Link href="/reports" className="text-sm font-semibold text-accent">
            View reports →
          </Link>
        </Card>
        <Card>
          <p className="text-sm text-muted">AI Tracker</p>
          <p className="text-base font-semibold text-navy">Build a KPI</p>
          <Link href="/ai-tracker" className="text-sm font-semibold text-accent">
            Open tracker →
          </Link>
        </Card>
      </div>

      <Card title="Recent activity">
        {audit.length === 0 ? (
          <p className="text-sm text-muted">No activity yet.</p>
        ) : (
          <ul className="divide-y divide-line">
            {audit.map((a, i) => (
              <li key={i} className="flex justify-between py-2 text-sm">
                <span className="text-navy">{a.action}</span>
                <span className="text-muted">
                  {new Date(a.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </AppShell>
  );
}
