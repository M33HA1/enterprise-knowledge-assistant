import { useEffect, useMemo, useState } from "react";
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
  CheckCircle2,
  ShieldCheck,
  Layers,
  Search,
  FileText,
  Users,
  Sparkles,
  Upload,
} from "lucide-react";

type TabKey = "chat" | "history" | "documents" | "admin";

const featureCards = [
  {
    title: "Trusted internal answers",
    description: "Deliver accurate, context-aware responses from your own policies and handbooks.",
    icon: Search,
  },
  {
    title: "Department-aware security",
    description: "Ensure employees see only the documents relevant to their division or role.",
    icon: ShieldCheck,
  },
  {
    title: "Fast document ingestion",
    description: "Upload and index manuals, handbooks, and SOPs instantly.",
    icon: Layers,
  },
];

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(localStorage.getItem("eka_access_token"));
  const [email, setEmail] = useState("admin@enterprise.com");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
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

  const tabs = useMemo(() => {
    const base: TabKey[] = ["chat", "history", "documents"];
    if (isAdmin) base.push("admin");
    return base;
  }, [isAdmin]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthCode = params.get("oauth_code");
    const oauthError = params.get("error");

    if (oauthError) {
      setError(oauthError);
      window.history.replaceState({}, "", window.location.pathname);
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
  }, [accessToken]);

  async function exchangeOAuthCode(oauthCode: string) {
    try {
      const res = await api.post("/auth/oauth/exchange", { oauth_code: oauthCode });
      const token = res.data.access_token as string;
      localStorage.setItem("eka_access_token", token);
      localStorage.setItem("eka_refresh_token", res.data.refresh_token as string);
      setAccessToken(token);
      setError("");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Google sign-in failed");
    }
  }

  async function bootstrap() {
    try {
      const me = await api.get<User>("/auth/me");
      setUser(me.data);
      await Promise.all([loadHistory(), loadDocuments(), loadDepartments()]);
      setError("");
    } catch {
      logout();
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
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Login failed");
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
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Google sign-in is not configured");
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
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.post<QueryResponse>("/query/", {
        question,
        department_filter: departmentFilter || undefined,
      });
      setAnswer(res.data);
      setQuestion("");
      await loadHistory();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Query failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory() {
    const res = await api.get("/query/history?page=1&page_size=20");
    setHistory(res.data.queries || []);
  }

  async function loadDocuments() {
    const res = await api.get("/documents?page=1&page_size=50");
    setDocuments(res.data.documents || []);
  }

  async function loadDepartments() {
    const res = await api.get<Department[]>("/admin/departments");
    setDepartments(res.data || []);
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
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const dashboardStats = useMemo(
    () => [
      { label: "Documents", value: documents.length, icon: FileText },
      { label: "Queries", value: history.length, icon: Search },
      { label: "Departments", value: departments.length, icon: Users },
    ],
    [documents.length, history.length, departments.length],
  );

  if (!user) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100">
        <div className="mx-auto flex min-h-screen max-w-[1300px] flex-col px-6 py-10 lg:px-8">
          <header className="flex flex-col gap-6 rounded-[2rem] border border-slate-800 bg-slate-900/80 p-6 shadow-[0_30px_120px_rgba(15,23,42,0.45)] backdrop-blur-xl md:flex-row md:items-center md:justify-between">
            <div className="space-y-3">
              <p className="text-sm uppercase tracking-[0.35em] text-indigo-300">Enterprise Knowledge Assistant</p>
              <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">Modern AI search for company policy and team knowledge.</h1>
              <p className="max-w-2xl text-base leading-7 text-slate-400">Secure access for employees to find official answers across internal documents and workflows.</p>
            </div>
            <div className="grid gap-4 sm:max-w-md">
              <div className="rounded-[1.75rem] border border-slate-800 bg-slate-950 p-6 shadow-xl shadow-slate-950/20">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Live demo</p>
                <p className="mt-4 text-lg font-semibold text-white">Sign in with Google or your company account.</p>
                <button onClick={loginWithGoogle} disabled={loading} className="mt-6 inline-flex items-center justify-center gap-2 rounded-full bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-60">
                  <Sparkles className="h-4 w-4" /> Continue with Google
                </button>
              </div>
            </div>
          </header>

          <main className="mt-10 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <section className="space-y-6">
              <div className="rounded-[2rem] border border-slate-800 bg-slate-900 p-8 shadow-[0_20px_60px_rgba(15,23,42,0.3)]">
                <p className="text-sm uppercase tracking-[0.35em] text-indigo-300">Why this assistant</p>
                <h2 className="mt-4 text-3xl font-semibold text-white">A polished knowledge experience for modern teams.</h2>
                <p className="mt-4 text-slate-400">Built using retrieval-augmented generation, this assistant connects employees with relevant policy documents and trusted answers.</p>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                {featureCards.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div key={item.title} className="rounded-[1.75rem] border border-slate-800 bg-slate-950 p-6 shadow-md shadow-slate-950/20">
                      <div className="inline-flex h-12 w-12 items-center justify-center rounded-3xl bg-indigo-600 text-white">
                        <Icon className="h-6 w-6" />
                      </div>
                      <h3 className="mt-5 text-xl font-semibold text-white">{item.title}</h3>
                      <p className="mt-3 text-sm leading-6 text-slate-400">{item.description}</p>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="rounded-[2rem] border border-slate-800 bg-slate-900 p-8 shadow-[0_20px_60px_rgba(15,23,42,0.25)]">
              <p className="text-sm uppercase tracking-[0.35em] text-indigo-300">Login</p>
              <h2 className="mt-4 text-3xl font-semibold text-white">Sign in to your knowledge hub</h2>
              <p className="mt-3 text-slate-400">Enter your credentials or use Google sign-in to access secure internal search.</p>
              {error && <div className="mt-6 rounded-3xl bg-rose-950/80 p-4 text-sm text-rose-300">{error}</div>}
              <form onSubmit={login} className="mt-6 space-y-4">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-300">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-3xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
                    placeholder="admin@enterprise.com"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-300">Password</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full rounded-3xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
                    placeholder="••••••••"
                  />
                </div>
                <button type="submit" disabled={loading} className="w-full rounded-3xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60">
                  {loading ? "Signing in..." : "Sign in"}
                </button>
                <button type="button" disabled={loading} onClick={loginWithGoogle} className="w-full rounded-3xl border border-slate-700 bg-slate-950 px-5 py-3 text-sm font-semibold text-slate-100 transition hover:bg-slate-800 disabled:opacity-60">
                  Continue with Google
                </button>
              </form>
            </section>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-[1420px] px-6 py-8 lg:px-8">
        <header className="mb-6 flex flex-col gap-4 rounded-[2rem] border border-slate-800 bg-slate-900/80 p-6 shadow-[0_30px_120px_rgba(15,23,42,0.45)] backdrop-blur-xl md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.35em] text-indigo-300">Enterprise Knowledge Assistant</p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight text-white sm:text-5xl">A professional internal AI assistant for secure policy search.</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-400">Get rapid, citation-backed responses from your company documents, with RBAC enforcement and intelligent department filtering.</p>
          </div>
          <div className="flex flex-col gap-3 rounded-[1.75rem] border border-slate-800 bg-slate-950 p-5 text-sm text-slate-300 shadow-xl shadow-slate-950/20">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Signed in as</p>
                <p className="mt-2 font-semibold text-white">{user.full_name}</p>
                <p className="text-sm text-slate-500">{user.email}</p>
              </div>
              <button onClick={logout} className="rounded-full border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-200 transition hover:bg-slate-800">Sign out</button>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {dashboardStats.map((stat) => {
                const Icon = stat.icon;
                return (
                  <div key={stat.label} className="rounded-3xl bg-slate-900 p-4">
                    <div className="flex items-center gap-3 text-slate-300">
                      <span className="inline-flex h-10 w-10 items-center justify-center rounded-3xl bg-slate-800 text-indigo-300">
                        <Icon className="h-5 w-5" />
                      </span>
                      <div>
                        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">{stat.label}</p>
                        <p className="mt-2 text-xl font-semibold text-white">{stat.value}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </header>

        <nav className="mb-6 flex flex-wrap gap-3 rounded-3xl border border-slate-800 bg-slate-900 p-3">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-full px-5 py-2 text-sm font-semibold transition ${activeTab === tab ? "bg-indigo-600 text-white" : "bg-slate-950 text-slate-300 hover:bg-slate-800"}`}
            >
              {tab}
            </button>
          ))}
        </nav>

        <div className="grid gap-6 xl:grid-cols-[1.55fr_0.85fr]">
          <section className="space-y-6">
            {activeTab === "chat" && (
              <article className="rounded-[2rem] border border-slate-800 bg-slate-900 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.25)]">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm uppercase tracking-[0.35em] text-indigo-300">Ask a question</p>
                    <h2 className="mt-3 text-3xl font-semibold text-white">Search your company knowledgebase.</h2>
                    <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Receive concise, referenced answers to employee questions.</p>
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-4 py-2 text-sm text-slate-300">
                    <Search className="h-4 w-4" /> Instant retrieval
                  </div>
                </div>
                <form onSubmit={askQuestion} className="mt-6 space-y-4">
                  <textarea
                    className="w-full rounded-[1.75rem] border border-slate-700 bg-slate-950 px-5 py-4 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
                    placeholder="Ask how to escalate a security incident, request PTO, or find policy details."
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                  />
                  {isAdmin && (
                    <select
                      className="w-full rounded-[1.75rem] border border-slate-700 bg-slate-950 px-5 py-4 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
                      value={departmentFilter}
                      onChange={(e) => setDepartmentFilter(e.target.value)}
                    >
                      <option value="">Search across all departments</option>
                      {departments.map((dept) => (
                        <option key={dept.id} value={dept.name}>{dept.name}</option>
                      ))}
                    </select>
                  )}
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <button
                      type="submit"
                      disabled={loading}
                      className="inline-flex items-center justify-center rounded-full bg-indigo-600 px-8 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {loading ? "Searching..." : "Ask the assistant"}
                    </button>
                    <p className="text-sm text-slate-500">Answers include citations, confidence, and escalation guidance.</p>
                  </div>
                </form>

                {error && <div className="mt-5 rounded-3xl bg-rose-950/80 p-4 text-sm text-rose-300">{error}</div>}

                {answer && (
                  <div className="mt-8 space-y-5 rounded-[1.75rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div>
                        <p className="text-sm uppercase tracking-[0.3em] text-slate-500">AI response</p>
                        <h3 className="mt-2 text-2xl font-semibold text-white">Answer summary</h3>
                      </div>
                      <div className="rounded-full bg-slate-900 px-4 py-2 text-xs uppercase tracking-[0.3em] text-slate-400">{answer.model_used}</div>
                    </div>
                    <div className="prose prose-invert max-w-none text-slate-100">
                      <p>{answer.answer}</p>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="rounded-3xl border border-slate-800 bg-slate-900 p-4">
                        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Confidence</p>
                        <p className="mt-2 text-xl font-semibold text-white">{answer.confidence.toFixed(2)}</p>
                      </div>
                      <div className="rounded-3xl border border-slate-800 bg-slate-900 p-4">
                        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Escalation</p>
                        <p className="mt-2 text-xl font-semibold text-white">{answer.needs_escalation ? "Recommended" : "Not required"}</p>
                      </div>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      {answer.sources.map((source, index) => (
                        <div key={`${source.document}-${index}`} className="rounded-3xl border border-slate-800 bg-slate-900 p-4">
                          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Document</p>
                          <p className="mt-2 text-sm font-semibold text-white">{source.document}</p>
                          <p className="mt-2 text-sm text-slate-400">Page {source.page} • Dept {source.department}</p>
                          <p className="mt-3 text-xs uppercase tracking-[0.3em] text-slate-500">Relevance score</p>
                          <p className="mt-1 text-sm text-indigo-300">{source.relevance_score}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </article>
            )}

            {activeTab === "history" && (
              <section className="rounded-[2rem] border border-slate-800 bg-slate-900 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.25)]">
                <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm uppercase tracking-[0.35em] text-indigo-300">Query history</p>
                    <h2 className="mt-3 text-3xl font-semibold text-white">Recent interactions</h2>
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-4 py-2 text-sm text-slate-300">
                    <FileText className="h-4 w-4" /> {history.length} queries
                  </div>
                </div>
                <div className="space-y-4">
                  {history.length === 0 ? (
                    <div className="rounded-[1.75rem] border border-dashed border-slate-700 bg-slate-950 p-8 text-center text-slate-400">No history yet — ask your first question to generate a query.</div>
                  ) : (
                    history.map((item) => (
                      <article key={item.id} className="rounded-[1.75rem] border border-slate-800 bg-slate-950 p-5">
                        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <p className="text-sm font-semibold text-white">{item.question}</p>
                            <p className="mt-2 text-sm text-slate-400">{item.answer}</p>
                          </div>
                          <div className="rounded-3xl bg-slate-900 px-4 py-2 text-xs uppercase tracking-[0.3em] text-slate-400">{item.needs_escalation ? "Escalated" : "Resolved"}</div>
                        </div>
                        <div className="mt-4 flex flex-wrap gap-3 text-xs uppercase tracking-[0.3em] text-slate-500">
                          <span>{item.confidence !== null ? `Confidence ${item.confidence.toFixed(2)}` : "No confidence"}</span>
                          <span>{new Date(item.created_at).toLocaleString()}</span>
                        </div>
                      </article>
                    ))
                  )}
                </div>
              </section>
            )}

            {activeTab === "documents" && (
              <section className="rounded-[2rem] border border-slate-800 bg-slate-900 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.25)]">
                <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm uppercase tracking-[0.35em] text-indigo-300">Knowledge base</p>
                    <h2 className="mt-3 text-3xl font-semibold text-white">Documents</h2>
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-4 py-2 text-sm text-slate-300">
                    <Layers className="h-4 w-4" /> {documents.length} documents
                  </div>
                </div>

                {isAdmin && (
                  <div className="mb-6 rounded-[1.75rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <span className="inline-flex h-10 w-10 items-center justify-center rounded-3xl bg-indigo-600 text-white">
                        <Upload className="h-5 w-5" />
                      </span>
                      <div>
                        <p className="text-sm font-semibold text-white">Upload new document</p>
                        <p className="text-xs text-slate-500">PDF, DOCX, or TXT (max 50MB)</p>
                      </div>
                    </div>
                    {uploadError && <div className="mb-4 rounded-3xl bg-rose-950/80 p-4 text-sm text-rose-300">{uploadError}</div>}
                    {uploadSuccess && <div className="mb-4 rounded-3xl bg-emerald-950/80 p-4 text-sm text-emerald-300">{uploadSuccess}</div>}
                    <form onSubmit={uploadDocument} className="space-y-4">
                      <div className="grid gap-4 sm:grid-cols-2">
                        <input
                          type="text"
                          placeholder="Document title (required)"
                          value={uploadTitle}
                          onChange={(e) => setUploadTitle(e.target.value)}
                          className="w-full rounded-3xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
                        />
                        <select
                          value={uploadDeptId}
                          onChange={(e) => setUploadDeptId(e.target.value)}
                          className="w-full rounded-3xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
                        >
                          <option value="">General (no department)</option>
                          {departments.map((dept) => (
                            <option key={dept.id} value={dept.id}>{dept.name}</option>
                          ))}
                        </select>
                      </div>
                      <label className="flex cursor-pointer flex-col items-center justify-center rounded-[1.75rem] border-2 border-dashed border-slate-700 bg-slate-900 p-6 text-center transition hover:border-indigo-500 hover:bg-slate-800/50">
                        <Upload className="mb-2 h-8 w-8 text-slate-500" />
                        <p className="text-sm text-slate-300">
                          {uploadFile ? uploadFile.name : "Click to select a file"}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">PDF, DOCX, or TXT</p>
                        <input
                          type="file"
                          accept=".pdf,.docx,.txt"
                          className="hidden"
                          onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                        />
                      </label>
                      <button
                        type="submit"
                        disabled={uploading || !uploadFile || !uploadTitle.trim()}
                        className="inline-flex items-center justify-center rounded-full bg-indigo-600 px-8 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {uploading ? "Uploading..." : "Upload document"}
                      </button>
                    </form>
                  </div>
                )}
                <div className="overflow-hidden rounded-3xl border border-slate-800">
                  <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
                    <thead className="bg-slate-950 text-slate-400">
                      <tr>
                        <th className="px-5 py-4">Title</th>
                        <th className="px-5 py-4">Type</th>
                        <th className="px-5 py-4">Status</th>
                        <th className="px-5 py-4">Department</th>
                        <th className="px-5 py-4">Chunks</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 bg-slate-950">
                      {documents.map((doc) => (
                        <tr key={doc.id} className="hover:bg-slate-900/80 transition-colors">
                          <td className="px-5 py-4 text-slate-100">{doc.title}</td>
                          <td className="px-5 py-4 text-slate-400">{doc.file_type}</td>
                          <td className="px-5 py-4 text-slate-400">{doc.status}</td>
                          <td className="px-5 py-4 text-slate-400">{doc.department_name || "general"}</td>
                          <td className="px-5 py-4 text-slate-400">{doc.chunk_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {activeTab === "admin" && isAdmin && (
              <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.25)]">
                <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm uppercase tracking-[0.35em] text-indigo-300">Admin panel</p>
                    <h2 className="mt-3 text-3xl font-semibold text-white">Departments</h2>
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-4 py-2 text-sm text-slate-300">
                    <Users className="h-4 w-4" /> {departments.length} groups
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  {departments.map((dept) => (
                    <div key={dept.id} className="rounded-3xl border border-slate-800 bg-slate-950 p-5">
                      <div className="flex items-center gap-3">
                        <span className="inline-flex h-11 w-11 items-center justify-center rounded-3xl bg-indigo-600 text-white"><CheckCircle2 className="h-5 w-5" /></span>
                        <div>
                          <p className="text-base font-semibold text-white">{dept.name}</p>
                          <p className="text-sm text-slate-500">Department</p>
                        </div>
                      </div>
                      <p className="mt-4 text-sm leading-6 text-slate-400">{dept.description || "No description provided."}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </section>

          <aside className="space-y-6">
            <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.25)]">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm uppercase tracking-[0.35em] text-indigo-300">Product highlights</p>
                  <h3 className="mt-3 text-xl font-semibold text-white">Designed for modern teams</h3>
                </div>
                <Sparkles className="h-6 w-6 text-indigo-400" />
              </div>
              <div className="mt-5 space-y-4 text-sm text-slate-400">
                <div className="rounded-3xl border border-slate-800 bg-slate-950 p-4">
                  <p className="font-semibold text-white">Secure by design</p>
                  <p>RBAC-aware search and encrypted sessions keep internal knowledge accessible only to authorized staff.</p>
                </div>
                <div className="rounded-3xl border border-slate-800 bg-slate-950 p-4">
                  <p className="font-semibold text-white">Actionable answers</p>
                  <p>The assistant returns citations, confidence scores, and escalation flags for trusted decision-making.</p>
                </div>
                <div className="rounded-3xl border border-slate-800 bg-slate-950 p-4">
                  <p className="font-semibold text-white">Enterprise-ready</p>
                  <p>Built for HR, legal, IT, and operations teams with document ingestion and lifecycle support.</p>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.25)]">
              <p className="text-sm uppercase tracking-[0.35em] text-indigo-300">Workflow</p>
              <h3 className="mt-3 text-xl font-semibold text-white">From documents to answers</h3>
              <div className="mt-5 space-y-4 text-sm text-slate-400">
                {[
                  { title: "Upload knowledge", description: "Ingest manuals, handbooks, and SOPs for immediate searchability." },
                  { title: "Search with AI", description: "Ask plain-language questions with department-aware context." },
                  { title: "Review results", description: "Use citations and confidence to validate every answer." },
                ].map((item) => (
                  <div key={item.title} className="rounded-3xl border border-slate-800 bg-slate-950 p-4">
                    <p className="font-semibold text-white">{item.title}</p>
                    <p className="mt-2 text-sm text-slate-400">{item.description}</p>
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}

export default App;
