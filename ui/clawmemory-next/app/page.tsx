"use client";

import { useEffect, useMemo, useState } from "react";
import { BellRing, Database, Search, TimerReset } from "lucide-react";
import { Card } from "@/components/card";

type Snapshot = {
  stats: Record<string, number>;
  timeline: Array<{ id: string; source: string; snippet?: string; text?: string; timestamp: string; tags?: string[] }>;
};

const API_BASE = process.env.NEXT_PUBLIC_CLAWMEMORY_API_BASE || "http://127.0.0.1:8787";

export default function Page() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Snapshot["timeline"]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/api/snapshot?limit=120`)
      .then((r) => r.json())
      .then((d) => {
        setSnapshot(d);
        setResults(d.timeline || []);
      })
      .catch(() => undefined);
  }, []);

  async function onSearch() {
    if (!query.trim()) {
      setResults(snapshot?.timeline || []);
      return;
    }
    const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}&k=20`);
    const data = await res.json();
    setResults(data.results || []);
  }

  const stats = useMemo(() => snapshot?.stats || {}, [snapshot]);

  return (
    <main className="mx-auto min-h-screen max-w-7xl p-6">
      <header className="mb-6 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight">ClawMemory UI</h1>
          <p className="mt-1 text-sm text-slate-600">Next.js + shadcn-style dashboard for local memory ops</p>
        </div>
        <div className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs">Self-host only</div>
      </header>

      <section className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card><div className="text-xs text-slate-500">Total Memories</div><div className="mt-2 text-2xl font-semibold">{stats.total_memories ?? 0}</div></Card>
        <Card><div className="text-xs text-slate-500">Reminder Pending</div><div className="mt-2 text-2xl font-semibold">{stats.reminders_pending ?? 0}</div></Card>
        <Card><div className="text-xs text-slate-500">Reminder Overdue</div><div className="mt-2 text-2xl font-semibold">{stats.reminders_overdue ?? 0}</div></Card>
        <Card><div className="text-xs text-slate-500">Session Buffers</div><div className="mt-2 text-2xl font-semibold">{stats.session_buffers ?? 0}</div></Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.5fr_0.9fr]">
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-medium">Memory Timeline</h2>
            <div className="flex items-center gap-2">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search memory"
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <button onClick={onSearch} className="rounded-lg bg-teal-600 px-3 py-2 text-sm text-white">
                <Search className="mr-1 inline h-4 w-4" /> Search
              </button>
            </div>
          </div>
          <div className="grid max-h-[560px] gap-2 overflow-auto">
            {results.map((row) => (
              <article key={row.id} className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>{row.source}</span>
                  <span>{new Date(row.timestamp).toLocaleString()}</span>
                </div>
                <p className="mt-1 text-sm text-slate-800">{row.snippet || row.text}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {(row.tags || []).map((t) => <span key={t} className="rounded-full border border-slate-300 px-2 py-0.5 text-[11px]">{t}</span>)}
                </div>
              </article>
            ))}
          </div>
        </Card>

        <div className="grid gap-4">
          <Card>
            <h3 className="mb-2 text-sm font-medium">Virtual Office</h3>
            <div className="relative h-40 rounded-xl border border-slate-300 bg-gradient-to-b from-blue-100 to-blue-300">
              <div className="absolute bottom-5 left-4 h-5 w-5 rounded-full border-2 border-green-900 bg-green-400" />
              <div className="absolute bottom-5 right-5 h-12 w-10 rounded-md border-2 border-slate-900 bg-slate-700" />
            </div>
            <p className="mt-2 text-xs text-slate-600">Agent goes to filing cabinet on distill/update memory actions.</p>
          </Card>

          <Card>
            <h3 className="mb-2 text-sm font-medium">Integrations</h3>
            <ul className="space-y-2 text-sm text-slate-700">
              <li><Database className="mr-2 inline h-4 w-4" /> ClawReceipt recurring finance capture</li>
              <li><TimerReset className="mr-2 inline h-4 w-4" /> ClawFlow cron + fail reminder memory</li>
              <li><BellRing className="mr-2 inline h-4 w-4" /> ClawWizard mode preference profile</li>
            </ul>
          </Card>
        </div>
      </section>
    </main>
  );
}
