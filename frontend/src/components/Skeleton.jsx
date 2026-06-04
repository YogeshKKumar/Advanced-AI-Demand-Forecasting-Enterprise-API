import React from "react";

export default function Skeleton({ className = "h-32" }) {
  return <div className={`animate-pulse rounded-lg bg-slate-200/70 dark:bg-white/10 ${className}`} />;
}


