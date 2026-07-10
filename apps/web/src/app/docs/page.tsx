import Link from "next/link";

import { Navbar } from "@/components/navbar";
import { Badge, Card } from "@/components/ui";

const ENDPOINTS: Array<{ method: string; path: string; desc: string; stub?: boolean }> = [
  { method: "GET", path: "/api/health", desc: "Liveness probe" },
  { method: "GET", path: "/api/tasks", desc: "List tasks from the input manifest" },
  {
    method: "POST",
    path: "/api/tasks",
    desc: "Submit task(s) {task_id, video_url, styles[]} — unknown styles dropped, same id replaces",
  },
  { method: "POST", path: "/api/tasks/run", desc: "Trigger a pipeline run (202; 409 if running)" },
  { method: "GET", path: "/api/tasks/run", desc: "Poll run status: idle / running / succeeded / failed" },
  { method: "GET", path: "/api/results", desc: "All clip results (empty until the pipeline runs)" },
  { method: "GET", path: "/api/results/{task_id}", desc: "Captions for one task (404 if unknown)" },
  { method: "GET", path: "/api/media/{filename}", desc: "Stream a file from the media dir" },
  { method: "POST", path: "/api/keys/validate", desc: "Check a Fireworks API key upstream" },
  { method: "POST", path: "/api/search", desc: "Semantic moment search", stub: true },
  { method: "POST", path: "/api/qa", desc: "Grounded RAG question-answering", stub: true },
];

export default function DocsPage() {
  return (
    <div>
      <Navbar />
      <div className="mx-auto max-w-4xl px-6 py-14">
        <h1 className="mb-2 text-3xl font-semibold tracking-tight">Documentation</h1>
        <p className="mb-10 text-muted">
          The frontend is a static export talking to the <code className="font-mono">services/api</code>{" "}
          FastAPI backend, which brokers the captioner pipeline. Full reference lives in the{" "}
          <a
            href="https://github.com/Katlego-tech/OmniCaption"
            className="text-primary-soft underline"
          >
            repository
          </a>
          .
        </p>

        <h2 className="mb-4 text-xl font-medium">Quickstart</h2>
        <Card className="mb-10">
          <pre className="overflow-x-auto text-sm leading-relaxed text-muted">
            {`# backend
cd services/api && pip install -r requirements.txt
uvicorn app.main:app --port 8000

# frontend (this app)
npm run dev --workspace apps/web    # http://localhost:3000

# queue a clip and run the pipeline
curl -X POST localhost:8000/api/tasks -H 'Content-Type: application/json' \\
  -d '[{"task_id":"v1","video_url":"https://…/clip.mp4","styles":["formal","sarcastic"]}]'
curl -X POST localhost:8000/api/tasks/run`}
          </pre>
        </Card>

        <h2 className="mb-4 text-xl font-medium">API reference</h2>
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Method</th>
                <th className="px-4 py-3 font-medium">Path</th>
                <th className="px-4 py-3 font-medium">Description</th>
              </tr>
            </thead>
            <tbody>
              {ENDPOINTS.map((endpoint) => (
                <tr
                  key={`${endpoint.method} ${endpoint.path}`}
                  className="border-b border-border/50 last:border-0"
                >
                  <td className="px-4 py-3 font-mono text-xs text-primary-soft">
                    {endpoint.method}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{endpoint.path}</td>
                  <td className="px-4 py-3 text-muted">
                    {endpoint.desc}{" "}
                    {endpoint.stub && <Badge tone="primary">501 · Track 3</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-10 text-sm text-faint">
          Configure the backend URL and your Fireworks key on the{" "}
          <Link href="/dashboard/accounts" className="text-primary-soft underline">
            Accounts page
          </Link>
          .
        </p>
      </div>
    </div>
  );
}
