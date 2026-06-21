"use client";

import { useEffect, useState } from "react";

import { AppShell, Card } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";

export default function AiTrackerPage() {
  const [datasets, setDatasets] = useState<{ id: string; name: string }[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [metricName, setMetricName] = useState("");
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const [formula, setFormula] = useState<{
    formula_id: string;
    expression: string;
    variables: string[];
    rationale?: string;
    status: string;
  } | null>(null);
  const [result, setResult] = useState<number | string | null>(null);

  useEffect(() => {
    api
      .listDatasets()
      .then((d) => {
        setDatasets(d);
        if (d[0]) setDatasetId(d[0].id);
      })
      .catch(() => {});
  }, []);

  async function propose() {
    setError("");
    setResult(null);
    setBusy("propose");
    try {
      const metric = await api.createMetric({
        name: metricName || goal,
        default_viz: "performance_bridge",
      });
      const f = await api.proposeFormula(metric.metric_id, {
        goal,
        dataset_id: datasetId,
      });
      setFormula(f);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Propose failed");
    } finally {
      setBusy("");
    }
  }

  async function validateAndRun() {
    if (!formula) return;
    setError("");
    setBusy("run");
    try {
      await api.validateFormula(formula.formula_id);
      setFormula({ ...formula, status: "validated" });
      const res = await api.executeFormula(formula.formula_id);
      setResult(res.result as number);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Execution failed");
    } finally {
      setBusy("");
    }
  }

  return (
    <AppShell>
      <h1 className="mb-2 text-3xl font-extrabold text-navy">AI Tracker</h1>
      <p className="mb-8 text-muted">
        Describe a KPI in plain language. The assistant proposes a formula; you validate
        it (the gate), then it runs against your data.
      </p>

      <div className="grid gap-6 md:grid-cols-2">
        <Card title="1 · Ask">
          <div className="space-y-4">
            <select
              className="field !rounded-xl !text-left"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
            >
              <option value="">Select a dataset</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
            <input
              className="field !rounded-xl !text-left"
              placeholder="Metric name (e.g. Win rate per training hour)"
              value={metricName}
              onChange={(e) => setMetricName(e.target.value)}
            />
            <input
              className="field !rounded-xl !text-left"
              placeholder="Goal, using your column names"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              className="btn-accent"
              disabled={!datasetId || !goal || busy !== ""}
              onClick={propose}
            >
              {busy === "propose" ? "Thinking..." : "Propose Formula"}
            </button>
          </div>
        </Card>

        <Card title="2 · Validate & Generate">
          {!formula ? (
            <p className="text-sm text-muted">The proposed formula will appear here.</p>
          ) : (
            <div className="space-y-4">
              <div className="rounded-xl bg-surface p-4">
                <p className="font-mono text-navy">{formula.expression}</p>
                <p className="mt-2 text-xs text-muted">
                  Uses: {formula.variables.join(", ")}
                </p>
                {formula.rationale && (
                  <p className="mt-1 text-xs text-muted">{formula.rationale}</p>
                )}
                <span className="mt-2 inline-block rounded-full bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent">
                  {formula.status}
                </span>
              </div>
              <button
                className="btn-navy"
                disabled={busy !== ""}
                onClick={validateAndRun}
              >
                {busy === "run" ? "Running..." : "Validate & Run"}
              </button>

              {result !== null && (
                <div className="rounded-xl border border-accent bg-accent-soft p-5 text-center">
                  <p className="text-sm text-muted">Result</p>
                  <p className="text-3xl font-extrabold text-navy">
                    {typeof result === "number" ? result.toFixed(4) : String(result)}
                  </p>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
