"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/lib/auth";

export default function Home() {
  const { session, ready } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (ready) router.replace(session ? "/dashboard" : "/login");
  }, [ready, session, router]);
  return null;
}
