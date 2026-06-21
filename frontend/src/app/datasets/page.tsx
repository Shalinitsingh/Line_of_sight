"use client";

import { useEffect, useRef, useState } from "react";

import { AppShell, Card } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";

interface DatasetRow {
  id: string;
  name: string;
  status: string;
  row_count: number;
}

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<DatasetRow[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [lastColumns, setLastColumns] = useState<
    { key: string; type: string; numeric: boolean }[] | null
  >(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    try {
      setDatasets(await api.listDatasets());
    } catch {
      /* ignore */
    }
  }
  useEffect(() => {
    refresh();
  }, []);

  async function upload() {
    setError("");
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Choose a CSV or Excel file");
      return;
    }
    setBusy(true);
    try {
      const res = await api.uploadDataset(file, name || file.name);
      setLastColumns(res.columns);
      setName("");
      if (fileRef.current) fileRef.current.value = "";
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <h1 className="mb-2 text-3xl font-extrabold text-navy">Data Ingestion</h1>
      <p className="mb-8 text-muted">
        Upload any CSV or Excel file. Columns are profiled automatically — no fixed
        schema required.
      </p>

      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Upload a dataset">
          <div className="space-y-4">
            <input
              className="field !rounded-xl !text-left"
              placeholder="Dataset name (optional)"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="block w-full text-sm text-navy file:mr-4 file:rounded-full file:border-0 file:bg-accent file:px-4 file:py-2 file:text-white"
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button className="btn-accent" disabled={busy} onClick={upload}>
              {busy ? "Uploading..." : "Upload & Profile"}
            </button>
          </div>

          {lastColumns && (
            <div className="mt-6">
              <p className="mb-2 text-sm font-semibold text-navy">Detected columns:</p>
              <div className="flex flex-wrap gap-2">
                {lastColumns.map((c) => (
                  <span
                    key={c.key}
                    className="rounded-full bg-surface px-3 py-1 text-xs text-navy"
                  >
                    {c.key}
                    <span className="ml-1 text-muted">
                      ({c.numeric ? "numeric" : c.type})
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card title="Your datasets">
          {datasets.length === 0 ? (
            <p className="text-sm text-muted">No datasets yet.</p>
          ) : (
            <ul className="divide-y divide-line">
              {datasets.map((d) => (
                <li key={d.id} className="flex items-center justify-between py-3">
                  <span className="font-medium text-navy">{d.name}</span>
                  <span className="text-sm text-muted">
                    {d.row_count} rows · {d.status}
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
