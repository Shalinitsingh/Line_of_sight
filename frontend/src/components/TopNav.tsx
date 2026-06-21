"use client";

import Link from "next/link";

export function TopNav({
  variant = "accent",
}: {
  variant?: "accent" | "navy" | "blue";
}) {
  const bg =
    variant === "navy" ? "bg-navy" : variant === "blue" ? "bg-brandblue" : "bg-accent";
  return (
    <nav className={`${bg} text-white`}>
      <div className="mx-auto flex max-w-6xl items-center justify-end gap-10 px-6 py-4 text-sm font-medium tracking-wide">
        <Link href="/about" className="opacity-90 hover:opacity-100">
          VIDEO TUTORIAL
        </Link>
        <Link href="/about" className="opacity-90 hover:opacity-100">
          FEATURES
        </Link>
        <Link href="/about" className="opacity-90 hover:opacity-100">
          ABOUT US
        </Link>
      </div>
    </nav>
  );
}
