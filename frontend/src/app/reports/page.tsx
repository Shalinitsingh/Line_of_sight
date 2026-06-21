"use client";

import { useEffect, useState } from "react";

import { AppShell, Card } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function ReportsPage() {
  const [reports, setReports] = useState<
    { id: string; title: string; created_at: string }[]
  >([]);
  const [title, setTitle] = useState("");

  async function refresh() {
    try {
      setReports(await api.listReports());
    } catch {
      /* ignore */
    }
  }
  useEffect(() => {
    refresh();
  }, []);

  async function create() {
    if (!title) return;
    await api.createReport({ title });
    setTitle("");
    refresh();
  }

  return (
    <AppShell>
      <h1 className="mb-8 text-3xl font-extrabold text-navy">Reports</h1>
      <div className="grid gap-6 md:grid-cols-2">
        <Card title="New report">
          <div className="space-y-4">
            <input
              className="field !rounded-xl !text-left"
              placeholder="Report title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <button className="btn-accent" onClick={create}>
              Create
            </button>
          </div>
        </Card>
        <Card title="Saved reports">
          {reports.length === 0 ? (
            <p className="text-sm text-muted">No reports yet.</p>
          ) : (
            <ul className="divide-y divide-line">
              {reports.map((r) => (
                <li key={r.id} className="flex justify-between py-3">
                  <span className="font-medium text-navy">{r.title}</span>
                  <span className="text-sm text-muted">
                    {new Date(r.created_at).toLocaleDateString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
