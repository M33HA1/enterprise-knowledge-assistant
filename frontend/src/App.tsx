import { useEffect, useMemo, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { FormEvent } from "react";
import { api } from "./api";
import type {
  Department,
  DocumentItem,
  QueryHistoryItem,
  QueryResponse,
  User,
} from "./types";
import {
  MessageSquare,
  Clock,
  FileText,
  ShieldCheck,
  Upload,
  LogOut,
  ChevronRight,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Users,
  Layers,
} from "lucide-react";

type ApiError = { response?: { data?: { detail?: string } } };
function apiErrMsg(err: unknown, fallback: string): string {
  return (err as ApiError)?.response?.data?.detail ?? fallback;
}
type TabKey = "chat" | "history" | "documents" | "admin";

function LoadingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" />
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 75 ? "bg-emerald-500" : pct >= 45 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-slate-400">Confidence</span>
        <span className="font-semibold text-slate-200">{pct}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={"h-full rounded-full transition-all duration-500 " + color}
          style={{ width: pct + "%" }}
        />
      </div>
    </div>
  );
}

function FileTypeIcon({ type }: { type: string }) {
  const t = type.toLowerCase();
  if (t === "pdf")
    return (
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-red-500/15 text-xs font-bold text-red-400">
        PDF
      </span>
    );
  if (t === "docx" || t === "doc")
    return (
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/15 text-xs font-bold text-blue-400">
        DOC
      </span>
    );
  return (
    <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-slate-500/15 text-xs font-bold text-slate-400">
      TXT
    </span>
  );
}

function StatusDot({ status }: { status: string }) {
  const s = status.toLowerCase();
  const color =
    s === "processed" || s === "active"
      ? "bg-emerald-500"
      : s === "processing"
        ? "bg-amber-500"
        : "bg-slate-500";
  return (
    <span className="flex items-center gap-1.5 text-xs text-slate-400">
      <span className={"h-1.5 w-1.5 rounded-full " + color} />
      {status}
    </span>
  );
}

// ---- LoginPage ----
interface LoginPageProps {
  email: string;
  setEmail: (v: string) => void;
  password: string;
  setPassword: (v: string) => void;
  error: string;
  loading: boolean;
  onLogin: (e: React.FormEvent) => void;
  onGoogle: () => void;
}

function LoginPage({
  email,
  setEmail,
  password,
  setPassword,
  error,
  loading,
  onLogin,
  onGoogle,
}: LoginPageProps) {
  return (
    <div className="flex min-h-screen bg-[#0a0a0f]">
      {/* Left panel */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden p-12 lg:flex">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-indigo-600/20 blur-3xl" />
          <div className="absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-violet-600/15 blur-3xl" />
          <div className="absolute left-1/2 top-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-500/10 blur-2xl" />
        </div>
        <div className="relative z-10">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span className="text-sm font-semibold tracking-wide text-slate-200">EKA</span>
          </div>
        </div>
        <div className="relative z-10 space-y-6">
          <div>
            <h1 className="text-4xl font-semibold leading-tight tracking-tight text-slate-100">
              Enterprise Knowledge<br />
              <span className="text-indigo-400">at your fingertips.</span>
            </h1>
            <p className="mt-4 text-base leading-relaxed text-slate-400">
              Secure, AI-powered search across your company's internal documents, policies, and handbooks.
            </p>
          </div>
          <ul className="space-y-4">
            {[
              { icon: ShieldCheck, title: "Department-aware security", desc: "RBAC enforcement keeps sensitive docs in the right hands." },
              { icon: MessageSquare, title: "Cited, confident answers", desc: "Every response includes sources, confidence, and escalation flags." },
              { icon: Layers, title: "Instant document ingestion", desc: "Upload PDFs, DOCX, and TXT files -- searchable in seconds." },
            ].map(({ icon: Icon, title, desc }) => (
              <li key={title} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-indigo-500/20 text-indigo-400">
                  <Icon className="h-3.5 w-3.5" />
                </span>
                <div>
                  <p className="text-sm font-medium text-slate-200">{title}</p>
                  <p className="text-xs leading-relaxed text-slate-500">{desc}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <div className="relative z-10">
          <p className="text-xs text-slate-600">&copy; {new Date().getFullYear()} Enterprise Knowledge Assistant</p>
        </div>
      </div>

      {/* Right panel */}
      <div className="flex w-full items-center justify-center p-8 lg:w-1/2">
        <div className="w-full max-w-sm space-y-6">
          <div className="flex items-center gap-2.5 lg:hidden">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span className="text-sm font-semibold tracking-wide text-slate-200">EKA</span>
          </div>
          <div>
            <h2 className="text-2xl font-semibold text-slate-100">Welcome back</h2>
            <p className="mt-1 text-sm text-slate-500">Sign in to your knowledge hub</p>
          </div>
          {error && (
            <div className="flex items-start gap-2.5 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
          <form onSubmit={onLogin} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium uppercase tracking-wider text-slate-500">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-[#1e1e2e] bg-[#111118] px-3.5 py-2.5 text-sm text-slate-100 outline-none transition-all duration-150 placeholder:text-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
                placeholder="you@company.com"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium uppercase tracking-wider text-slate-500">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-[#1e1e2e] bg-[#111118] px-3.5 py-2.5 text-sm text-slate-100 outline-none transition-all duration-150 placeholder:text-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
                placeholder="........"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition-all duration-150 hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? <LoadingDots /> : "Sign in"}
            </button>
          </form>
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[#1e1e2e]" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-[#0a0a0f] px-3 text-xs text-slate-600">or</span>
            </div>
          </div>
          <button
            type="button"
            disabled={loading}
            onClick={onGoogle}
            className="flex w-full items-center justify-center gap-2.5 rounded-lg border border-[#1e1e2e] bg-[#111118] px-4 py-2.5 text-sm font-medium text-slate-300 transition-all duration-150 hover:border-slate-600 hover:bg-[#16161f] disabled:opacity-60"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Continue with Google
          </button>
        </div>
      </div>
    </div>
  );
}

// ---- Sidebar ----
interface SidebarProps {
  activeTab: TabKey;
  setActiveTab: (t: TabKey) => void;
  isAdmin: boolean;
  user: User;
  onLogout: () => void;
}

const NAV_ITEMS: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: "chat", label: "Chat", icon: MessageSquare },
  { key: "history", label: "History", icon: Clock },
  { key: "documents", label: "Documents", icon: FileText },
];

function Sidebar({ activeTab, setActiveTab, isAdmin, user, onLogout }: SidebarProps) {
  const items = isAdmin
    ? [...NAV_ITEMS, { key: "admin" as TabKey, label: "Admin", icon: ShieldCheck }]
    : NAV_ITEMS;

  const initials = user.full_name
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r border-[#1e1e2e] bg-[#111118]">
      <div className="flex h-14 items-center gap-2.5 border-b border-[#1e1e2e] px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-indigo-500">
          <Sparkles className="h-3.5 w-3.5 text-white" />
        </div>
        <span className="text-sm font-semibold tracking-wide text-slate-200">EKA</span>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
        <p className="mb-2 px-2 text-xs font-medium uppercase tracking-wider text-slate-600">Navigation</p>
        {items.map(({ key, label, icon: Icon }) => {
          const active = activeTab === key;
          return (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={
                "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-all duration-150 " +
                (active
                  ? "border-l-2 border-indigo-500 bg-indigo-500/10 pl-[10px] font-medium text-indigo-400"
                  : "border-l-2 border-transparent text-slate-400 hover:bg-[#1a1a24] hover:text-slate-200")
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
              {active && <ChevronRight className="ml-auto h-3.5 w-3.5 text-indigo-500" />}
            </button>
          );
        })}
      </nav>
      <div className="border-t border-[#1e1e2e] p-3">
        <div className="flex items-center gap-3 rounded-md px-2 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-semibold text-indigo-400">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-slate-200">{user.full_name}</p>
            <p className="truncate text-xs text-slate-600">{user.email}</p>
          </div>
          <button
            onClick={onLogout}
            title="Sign out"
            className="shrink-0 rounded-md p-1.5 text-slate-500 transition-all duration-150 hover:bg-[#1e1e2e] hover:text-slate-300"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}

// ---- ChatTab ----
interface ChatTabProps {
  question: string;
  setQuestion: (v: string) => void;
  lastQuestion: string;
  llmProvider: string;
  setLlmProvider: (v: string) => void;
  departmentFilter: string;
  setDepartmentFilter: (v: string) => void;
  departments: Department[];
  isAdmin: boolean;
  loading: boolean;
  error: string;
  answer: QueryResponse | null;
  onSubmit: (e: FormEvent) => void;
}

function ChatTab({
  question,
  setQuestion,
  lastQuestion,
  llmProvider,
  setLlmProvider,
  departmentFilter,
  setDepartmentFilter,
  departments,
  isAdmin,
  loading,
  error,
  answer,
  onSubmit,
}: ChatTabProps) {
  return (
    <div className="flex h-full flex-col gap-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Chat</h2>
          <p className="text-sm text-slate-500">Ask questions about your company knowledge base.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-500">Model:</span>
          <select
            value={llmProvider}
            onChange={(e) => setLlmProvider(e.target.value)}
            className="rounded-lg border border-[#1e1e2e] bg-[#111118] px-3 py-1.5 text-xs text-slate-300 outline-none transition-all duration-150 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
          >
            <option value="">Default</option>
            <option value="openai">OpenAI (GPT-4o-mini)</option>
            <option value="claude">Claude (3.5 Sonnet)</option>
            <option value="gemini">Gemini (2.0 Flash)</option>
            <option value="grok">Grok (xAI)</option>
          </select>
        </div>
      </div>

      {answer && (
        <div className="space-y-3">
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="flex justify-end">
            <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-indigo-500 px-4 py-3 text-sm text-white shadow-lg shadow-indigo-500/20">
              <p>{lastQuestion}</p>
            </div>
          </motion.div>
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="flex justify-start">
            <div className="max-w-[85%] space-y-4 rounded-2xl rounded-tl-sm border border-[#1e1e2e] bg-[#111118] px-5 py-4 shadow-xl">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-500/20">
                    <Sparkles className="h-3 w-3 text-indigo-400" />
                  </div>
                  <span className="text-xs font-medium text-slate-400">AI Answer</span>
                </div>
                <span className="rounded-full border border-[#1e1e2e] px-2.5 py-0.5 text-xs text-slate-500">
                  {answer.model_used}
                </span>
              </div>
              <p className="text-sm leading-relaxed text-slate-200">{answer.answer}</p>
              <ConfidenceBar value={answer.confidence} />
              {answer.needs_escalation && (
                <div className="flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs font-medium text-amber-400">
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                  Escalation recommended -- please consult your manager or HR.
                </div>
              )}
              {answer.sources.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-xs font-medium uppercase tracking-wider text-slate-600">Sources</p>
                  <div className="flex flex-wrap gap-2">
                    {answer.sources.map((src, i) => (
                      <span
                        key={src.document + "-" + i}
                        className="inline-flex items-center gap-1.5 rounded-full border border-[#1e1e2e] bg-[#0a0a0f] px-2.5 py-1 text-xs text-slate-400 transition-all duration-150 hover:border-slate-600"
                        title={"Dept: " + src.department + " | Page: " + src.page + " | Score: " + src.relevance_score}
                      >
                        <FileText className="h-3 w-3 text-indigo-400" />
                        {src.document}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex flex-wrap gap-3 border-t border-[#1e1e2e] pt-3 text-xs text-slate-600">
                <span>{answer.chunks_retrieved} chunks retrieved</span>
                <span>{answer.tokens_used} tokens</span>
                <span>{answer.response_time_ms}ms</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2.5 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={onSubmit} className="mt-auto space-y-3">
        {isAdmin && (
          <select
            className="w-full rounded-lg border border-[#1e1e2e] bg-[#111118] px-3.5 py-2.5 text-sm text-slate-300 outline-none transition-all duration-150 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
          >
            <option value="">All departments</option>
            {departments.map((dept) => (
              <option key={dept.id} value={dept.name}>{dept.name}</option>
            ))}
          </select>
        )}
        <div className="flex gap-2">
          <textarea
            rows={3}
            className="flex-1 resize-none rounded-lg border border-[#1e1e2e] bg-[#111118] px-3.5 py-2.5 text-sm text-slate-100 outline-none transition-all duration-150 placeholder:text-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
            placeholder="Ask about company policy, procedures, or any internal topic..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (question.trim() && !loading) onSubmit(e as unknown as FormEvent);
              }
            }}
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="self-end rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition-all duration-150 hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? <LoadingDots /> : "Send"}
          </button>
        </div>
        <p className="text-xs text-slate-600">Press Enter to send, Shift+Enter for new line.</p>
      </form>
    </div>
  );
}

// ---- HistoryTab ----
function HistoryTab({ history }: { history: QueryHistoryItem[] }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-100">History</h2>
        <p className="text-sm text-slate-500">{history.length} recent queries</p>
      </div>
      {history.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[#1e1e2e] py-16 text-center">
          <Clock className="mb-3 h-8 w-8 text-slate-700" />
          <p className="text-sm font-medium text-slate-500">No history yet</p>
          <p className="mt-1 text-xs text-slate-700">Ask your first question to see it here.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {history.map((item) => {
            const resolved = !item.needs_escalation;
            const conf = item.confidence ?? 0;
            const confPct = Math.round(conf * 100);
            return (
              <motion.article
                key={item.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.05 * Math.min(10, history.indexOf(item)) }}
                className={
                  "group relative rounded-xl border border-[#1e1e2e] bg-[#111118] p-4 transition-all duration-150 hover:border-slate-700 " +
                  (resolved ? "border-l-[3px] border-l-emerald-500 pl-4" : "border-l-[3px] border-l-amber-500 pl-4")
                }
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-100">{item.question}</p>
                    <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-500">{item.answer}</p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1.5">
                    <span
                      className={
                        "rounded-full px-2 py-0.5 text-xs font-medium " +
                        (resolved ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400")
                      }
                    >
                      {resolved ? "Resolved" : "Escalated"}
                    </span>
                    <span className="rounded-full border border-[#1e1e2e] px-2 py-0.5 text-xs text-slate-500">
                      {confPct}% conf
                    </span>
                  </div>
                </div>
                <p className="mt-2 text-xs text-slate-700">
                  {new Date(item.created_at).toLocaleString()}
                </p>
              </motion.article>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---- DocumentsTab ----
interface DocumentsTabProps {
  documents: DocumentItem[];
  departments: Department[];
  isAdmin: boolean;
  uploadFile: File | null;
  setUploadFile: (f: File | null) => void;
  uploadTitle: string;
  setUploadTitle: (v: string) => void;
  uploadDeptId: string;
  setUploadDeptId: (v: string) => void;
  uploading: boolean;
  uploadError: string;
  uploadSuccess: string;
  onUpload: (e: FormEvent) => void;
}

function DocumentsTab({
  documents,
  departments,
  isAdmin,
  uploadFile,
  setUploadFile,
  uploadTitle,
  setUploadTitle,
  uploadDeptId,
  setUploadDeptId,
  uploading,
  uploadError,
  uploadSuccess,
  onUpload,
}: DocumentsTabProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-100">Documents</h2>
        <p className="text-sm text-slate-500">{documents.length} documents in the knowledge base</p>
      </div>

      {isAdmin && (
        <div className="rounded-xl border border-[#1e1e2e] bg-[#111118] p-5">
          <div className="mb-4 flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-400">
              <Upload className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-200">Upload document</p>
              <p className="text-xs text-slate-600">PDF, DOCX, or TXT (max 50MB)</p>
            </div>
          </div>
          {uploadError && (
            <div className="mb-3 flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2.5 text-xs text-red-400">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {uploadError}
            </div>
          )}
          {uploadSuccess && (
            <div className="mb-3 flex items-start gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2.5 text-xs text-emerald-400">
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {uploadSuccess}
            </div>
          )}
          <form onSubmit={onUpload} className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                type="text"
                placeholder="Document title (required)"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                className="w-full rounded-lg border border-[#1e1e2e] bg-[#0a0a0f] px-3.5 py-2.5 text-sm text-slate-100 outline-none transition-all duration-150 placeholder:text-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
              />
              <select
                value={uploadDeptId}
                onChange={(e) => setUploadDeptId(e.target.value)}
                className="w-full rounded-lg border border-[#1e1e2e] bg-[#0a0a0f] px-3.5 py-2.5 text-sm text-slate-300 outline-none transition-all duration-150 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
              >
                <option value="">General (no department)</option>
                {departments.map((dept) => (
                  <option key={dept.id} value={dept.id}>{dept.name}</option>
                ))}
              </select>
            </div>
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-[#1e1e2e] bg-[#0a0a0f] p-6 text-center transition-all duration-150 hover:border-indigo-500/50 hover:bg-[#0d0d14]">
              <Upload className="mb-2 h-6 w-6 text-slate-600" />
              <p className="text-sm text-slate-400">
                {uploadFile ? uploadFile.name : "Click to select a file"}
              </p>
              <p className="mt-1 text-xs text-slate-600">PDF, DOCX, or TXT</p>
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                className="hidden"
                onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              />
            </label>
            <button
              type="submit"
              disabled={uploading || !uploadFile || !uploadTitle.trim()}
              className="flex items-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition-all duration-150 hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {uploading ? <LoadingDots /> : <><Upload className="h-3.5 w-3.5" /> Upload</>}
            </button>
          </form>
        </div>
      )}

      {documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[#1e1e2e] py-16 text-center">
          <FileText className="mb-3 h-8 w-8 text-slate-700" />
          <p className="text-sm font-medium text-slate-500">No documents yet</p>
          <p className="mt-1 text-xs text-slate-700">Upload your first document to get started.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {documents.map((doc) => (
            <motion.div
              key={doc.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * Math.min(10, documents.indexOf(doc)) }}
              whileHover={{ y: -2 }}
              className="group rounded-xl border border-[#1e1e2e] bg-[#111118] p-4 shadow-lg transition-all duration-150 hover:border-slate-600"
            >
              <div className="flex items-start gap-3">
                <FileTypeIcon type={doc.file_type} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-slate-100">{doc.title}</p>
                  <p className="mt-0.5 truncate text-xs text-slate-600">{doc.filename}</p>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {doc.department_name && (
                  <span className="rounded-full border border-[#1e1e2e] bg-[#0a0a0f] px-2 py-0.5 text-xs text-slate-400">
                    {doc.department_name}
                  </span>
                )}
                <span className="rounded-full border border-[#1e1e2e] bg-[#0a0a0f] px-2 py-0.5 text-xs text-slate-500">
                  {doc.chunk_count} chunks
                </span>
              </div>
              <div className="mt-3">
                <StatusDot status={doc.status} />
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---- AdminTab ----
interface AdminTabProps {
  departments: Department[];
  documents: DocumentItem[];
  uploadFile: File | null;
  setUploadFile: (f: File | null) => void;
  uploadTitle: string;
  setUploadTitle: (v: string) => void;
  uploadDeptId: string;
  setUploadDeptId: (v: string) => void;
  uploading: boolean;
  uploadError: string;
  uploadSuccess: string;
  onUpload: (e: FormEvent) => void;
}

function AdminTab({
  departments,
  documents,
  uploadFile,
  setUploadFile,
  uploadTitle,
  setUploadTitle,
  uploadDeptId,
  setUploadDeptId,
  uploading,
  uploadError,
  uploadSuccess,
  onUpload,
}: AdminTabProps) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-slate-100">Admin</h2>
        <p className="text-sm text-slate-500">Manage departments and upload documents.</p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Left: Department cards */}
        <div className="space-y-3">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-600">Departments</p>
          {departments.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[#1e1e2e] py-10 text-center">
              <Users className="mb-2 h-7 w-7 text-slate-700" />
              <p className="text-sm text-slate-600">No departments found</p>
            </div>
          ) : (
            departments.map((dept) => {
              const deptDocs = documents.filter((d) => d.department_name === dept.name);
              return (
                <div
                  key={dept.id}
                  className="rounded-xl border border-[#1e1e2e] bg-[#111118] p-4 transition-all duration-150 hover:border-slate-700"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-400">
                      <CheckCircle2 className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-slate-100">{dept.name}</p>
                      {dept.description && (
                        <p className="mt-0.5 truncate text-xs text-slate-600">{dept.description}</p>
                      )}
                    </div>
                  </div>
                  <div className="mt-3 flex gap-3">
                    <span className="flex items-center gap-1.5 text-xs text-slate-500">
                      <FileText className="h-3 w-3" />
                      {deptDocs.length} docs
                    </span>
                    <span className="flex items-center gap-1.5 text-xs text-slate-500">
                      <Layers className="h-3 w-3" />
                      {deptDocs.reduce((sum, d) => sum + d.chunk_count, 0)} chunks
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right: Upload form */}
        <div className="space-y-3">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-600">Upload Document</p>
          <div className="rounded-xl border border-[#1e1e2e] bg-[#111118] p-5">
            {uploadError && (
              <div className="mb-3 flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2.5 text-xs text-red-400">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {uploadError}
              </div>
            )}
            {uploadSuccess && (
              <div className="mb-3 flex items-start gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2.5 text-xs text-emerald-400">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {uploadSuccess}
              </div>
            )}
            <form onSubmit={onUpload} className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium uppercase tracking-wider text-slate-600">Title</label>
                <input
                  type="text"
                  placeholder="Document title (required)"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="w-full rounded-lg border border-[#1e1e2e] bg-[#0a0a0f] px-3.5 py-2.5 text-sm text-slate-100 outline-none transition-all duration-150 placeholder:text-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium uppercase tracking-wider text-slate-600">Department</label>
                <select
                  value={uploadDeptId}
                  onChange={(e) => setUploadDeptId(e.target.value)}
                  className="w-full rounded-lg border border-[#1e1e2e] bg-[#0a0a0f] px-3.5 py-2.5 text-sm text-slate-300 outline-none transition-all duration-150 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
                >
                  <option value="">General (no department)</option>
                  {departments.map((dept) => (
                    <option key={dept.id} value={dept.id}>{dept.name}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium uppercase tracking-wider text-slate-600">File</label>
                <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-[#1e1e2e] bg-[#0a0a0f] p-5 text-center transition-all duration-150 hover:border-indigo-500/50 hover:bg-[#0d0d14]">
                  <Upload className="mb-2 h-5 w-5 text-slate-600" />
                  <p className="text-sm text-slate-400">
                    {uploadFile ? uploadFile.name : "Click to select a file"}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">PDF, DOCX, or TXT (max 50MB)</p>
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    className="hidden"
                    onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  />
                </label>
              </div>
              <button
                type="submit"
                disabled={uploading || !uploadFile || !uploadTitle.trim()}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition-all duration-150 hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {uploading ? <LoadingDots /> : <><Upload className="h-3.5 w-3.5" /> Upload document</>}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Main App ----
function App() {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(
    localStorage.getItem("eka_access_token"),
  );
  const [email, setEmail] = useState("admin@enterprise.com");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [lastQuestion, setLastQuestion] = useState("");
  const [llmProvider, setLlmProvider] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [answer, setAnswer] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [activeTab, setActiveTab] = useState<TabKey>("chat");
  const [loading, setLoading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadDeptId, setUploadDeptId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState("");

  const isAdmin = user?.role === "admin" || user?.role === "super_admin";

  // Keep tabs list in sync with admin status
  const _tabs = useMemo(() => {
    const base: TabKey[] = ["chat", "history", "documents"];
    if (isAdmin) base.push("admin");
    return base;
  }, [isAdmin]);
  // _tabs is used to ensure admin tab is only accessible when isAdmin
  void _tabs;

  const isSubmitting = useRef(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthCode = params.get("oauth_code");
    const oauthError = params.get("error");
    if (oauthError) {
      window.history.replaceState({}, "", window.location.pathname);
      setTimeout(() => setError(oauthError), 0);
      return;
    }
    if (oauthCode) {
      void exchangeOAuthCode(oauthCode);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  useEffect(() => {
    if (!accessToken) return;
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  // Listen for forced logout events dispatched by the API interceptor
  // (triggered when token refresh fails — refresh token expired or revoked)
  useEffect(() => {
    const handleForcedLogout = () => logout();
    window.addEventListener("eka:logout", handleForcedLogout);
    return () => window.removeEventListener("eka:logout", handleForcedLogout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function exchangeOAuthCode(oauthCode: string) {
    try {
      const res = await api.post("/auth/oauth/exchange", { oauth_code: oauthCode });
      const token = res.data.access_token as string;
      localStorage.setItem("eka_access_token", token);
      localStorage.setItem("eka_refresh_token", res.data.refresh_token as string);
      setAccessToken(token);
      setError("");
    } catch (err: unknown) {
      setError(apiErrMsg(err, "Google sign-in failed"));
    }
  }

  async function bootstrap() {
    try {
      const me = await api.get<User>("/auth/me");
      setUser(me.data);
      setError("");
    } catch {
      // Only logout if /auth/me fails (invalid/expired token)
      logout();
      return;
    }
    // Load data separately — errors here should NOT log the user out
    try {
      await Promise.all([loadHistory(), loadDocuments(), loadDepartments()]);
    } catch {
      // Non-critical: data failed to load but user is still authenticated
      // Will retry on next interaction
    }
  }

  async function login(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/auth/login", { email, password });
      const token = res.data.access_token as string;
      localStorage.setItem("eka_access_token", token);
      localStorage.setItem("eka_refresh_token", res.data.refresh_token as string);
      setAccessToken(token);
    } catch (err: unknown) {
      setError(apiErrMsg(err, "Login failed"));
    } finally {
      setLoading(false);
    }
  }

  async function loginWithGoogle() {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<{ auth_url: string }>("/auth/google/login");
      window.location.href = res.data.auth_url;
    } catch (err: unknown) {
      setError(apiErrMsg(err, "Google sign-in is not configured"));
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("eka_access_token");
    localStorage.removeItem("eka_refresh_token");
    setAccessToken(null);
    setUser(null);
    setAnswer(null);
    setHistory([]);
    setDocuments([]);
    setDepartments([]);
  }

  async function askQuestion(e: FormEvent) {
    e.preventDefault();
    if (!question.trim() || isSubmitting.current) return;
    
    isSubmitting.current = true;
    setLoading(true);
    setError("");
    const asked = question.trim();
    try {
      const res = await api.post<QueryResponse>("/query/", {
        question: asked,
        department_filter: departmentFilter || undefined,
        llm_provider: llmProvider || undefined,
      });
      setLastQuestion(asked);
      setAnswer(res.data);
      setQuestion("");
      await loadHistory();
    } catch (err: unknown) {
      setError(apiErrMsg(err, "Query failed"));
    } finally {
      isSubmitting.current = false;
      setLoading(false);
    }
  }

  async function loadHistory() {
    try {
      const res = await api.get("/query/history?page=1&page_size=20");
      setHistory(res.data.queries || []);
    } catch {
      // Non-critical — leave existing state
    }
  }

  async function loadDocuments() {
    try {
      const res = await api.get("/documents/?page=1&page_size=50");
      setDocuments(res.data.documents || []);
    } catch {
      // Non-critical — leave existing state
    }
  }

  async function loadDepartments() {
    try {
      const res = await api.get<Department[]>("/admin/departments");
      setDepartments(res.data || []);
    } catch {
      // Non-critical — leave existing state
    }
  }

  async function uploadDocument(e: FormEvent) {
    e.preventDefault();
    if (!uploadFile || !uploadTitle.trim()) return;
    const ext = uploadFile.name.split(".").pop()?.toLowerCase();
    if (!ext || !["pdf", "docx", "txt"].includes(ext)) {
      setUploadError("Only PDF, DOCX, and TXT files are allowed.");
      return;
    }
    if (uploadFile.size > 50 * 1024 * 1024) {
      setUploadError("File size must be less than 50MB.");
      return;
    }
    setUploading(true);
    setUploadError("");
    setUploadSuccess("");
    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      formData.append("title", uploadTitle.trim());
      if (uploadDeptId) formData.append("department_id", uploadDeptId);
      await api.post("/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadSuccess("Document uploaded and processed successfully!");
      setUploadFile(null);
      setUploadTitle("");
      setUploadDeptId("");
      await loadDocuments();
    } catch (err: unknown) {
      setUploadError(apiErrMsg(err, "Upload failed"));
    } finally {
      setUploading(false);
    }
  }

  // Unauthenticated: show login page
  if (!user) {
    return (
      <LoginPage
        email={email}
        setEmail={setEmail}
        password={password}
        setPassword={setPassword}
        error={error}
        loading={loading}
        onLogin={login}
        onGoogle={loginWithGoogle}
      />
    );
  }

  // Authenticated: sidebar layout
  const uploadProps = {
    uploadFile,
    setUploadFile,
    uploadTitle,
    setUploadTitle,
    uploadDeptId,
    setUploadDeptId,
    uploading,
    uploadError,
    uploadSuccess,
    onUpload: uploadDocument,
  };

  return (
    <div className="flex min-h-screen bg-[#0a0a0f] text-[#f1f5f9]">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isAdmin={isAdmin}
        user={user}
        onLogout={logout}
      />

      {/* Main content area */}
      <main className="ml-60 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-4xl px-6 py-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {activeTab === "chat" && (
            <ChatTab
              question={question}
              setQuestion={setQuestion}
              lastQuestion={lastQuestion}
              llmProvider={llmProvider}
              setLlmProvider={setLlmProvider}
              departmentFilter={departmentFilter}
              setDepartmentFilter={setDepartmentFilter}
              departments={departments}
              isAdmin={isAdmin}
              loading={loading}
              error={error}
              answer={answer}
              onSubmit={askQuestion}
            />
          )}
          {activeTab === "history" && <HistoryTab history={history} />}
          {activeTab === "documents" && (
            <DocumentsTab
              documents={documents}
              departments={departments}
              isAdmin={isAdmin}
              {...uploadProps}
            />
          )}
          {activeTab === "admin" && isAdmin && (
            <AdminTab
              departments={departments}
              documents={documents}
              {...uploadProps}
            />
          )}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

export default App;
