"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type Industry = "corporate" | "hospital";

interface ThemeCtx {
  industry: Industry;
  setIndustry: (i: Industry) => void;
}

const Ctx = createContext<ThemeCtx>({ industry: "corporate", setIndustry: () => {} });

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [industry, setIndustryState] = useState<Industry>("corporate");

  useEffect(() => {
    const saved = (typeof window !== "undefined" &&
      window.localStorage.getItem("los_industry")) as Industry | null;
    if (saved === "corporate" || saved === "hospital") setIndustryState(saved);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", industry);
  }, [industry]);

  const setIndustry = (i: Industry) => {
    setIndustryState(i);
    window.localStorage.setItem("los_industry", i);
    document.documentElement.setAttribute("data-theme", i);
  };

  return <Ctx.Provider value={{ industry, setIndustry }}>{children}</Ctx.Provider>;
}

export const useTheme = () => useContext(Ctx);
