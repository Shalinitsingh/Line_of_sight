"use client";

import { useTheme } from "@/lib/theme";

function Switch({ on, color }: { on: boolean; color: string }) {
  return (
    <span
      className="relative inline-block h-6 w-11 rounded-full transition"
      style={{ background: on ? color : "#cbd2dd" }}
    >
      <span
        className="absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all"
        style={{ left: on ? "1.5rem" : "0.125rem" }}
      />
    </span>
  );
}

export function IndustryToggle() {
  const { industry, setIndustry } = useTheme();
  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => setIndustry("corporate")}
        className="flex w-40 items-center justify-between"
      >
        <span className="text-sm font-semibold text-navy">Corporate</span>
        <Switch on={industry === "corporate"} color="#c77f2e" />
      </button>
      <button
        type="button"
        onClick={() => setIndustry("hospital")}
        className="flex w-40 items-center justify-between"
      >
        <span className="text-sm font-semibold text-navy">Hospital</span>
        <Switch on={industry === "hospital"} color="#3d7b7c" />
      </button>
    </div>
  );
}
