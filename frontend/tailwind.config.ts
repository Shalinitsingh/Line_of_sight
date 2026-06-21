import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 60-30-10 palette from the Figma
        bg: "#FFFFFF",
        surface: "#F4F6F9",
        navy: "#1B2A4A",      // 30%
        "navy-deep": "#16243F",
        brandblue: "#4F79C7",
        muted: "#6B7280",
        line: "#E2E6EC",
        // 10% accent — driven by industry theme via CSS vars
        accent: "var(--accent)",
        "accent-hover": "var(--accent-hover)",
        "accent-soft": "var(--accent-soft)",
      },
      fontFamily: { sans: ["var(--font-inter)", "system-ui", "sans-serif"] },
      borderRadius: { xl2: "1.25rem" },
      boxShadow: { card: "0 10px 30px -12px rgba(27,42,74,0.18)" },
    },
  },
  plugins: [],
};
export default config;
