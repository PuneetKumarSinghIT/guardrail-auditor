import { useState } from "react";
import type { Finding } from "../lib/types";
import { hasFix, severityBadgeClass } from "../lib/risk";

interface AiExplanationPanelProps {
  finding: Finding | null;
  onClose: () => void;
}

// Slide-in drawer (right side, 480px). Tab 1: AI explanation + metadata.
// Tab 2 (CRITICAL/HIGH only): AI-generated fix code with a copy button.
export function AiExplanationPanel({ finding, onClose }: AiExplanationPanelProps) {
  const [tab, setTab] = useState<"explanation" | "fix">("explanation");
  const [copied, setCopied] = useState(false);

  const open = finding !== null;
  const showFix = finding ? hasFix(finding) : false;

  const copyFix = async () => {
    if (!finding?.ai_fix_code) return;
    await navigator.clipboard.writeText(finding.ai_fix_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-slate-900/40 transition-opacity ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <aside
        className={`fixed right-0 top-0 z-50 flex h-full w-[480px] max-w-full flex-col bg-white shadow-2xl transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        aria-hidden={!open}
      >
        {finding && (
          <>
            <header className="flex items-start justify-between border-b border-slate-200 p-5">
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-bold ${severityBadgeClass(
                      finding.severity
                    )}`}
                  >
                    {finding.severity}
                  </span>
                  <span className="font-mono text-sm font-semibold text-slate-700">
                    {finding.rule_id}
                  </span>
                </div>
                <h2 className="mt-2 text-lg font-semibold text-slate-900">
                  {finding.resource_name}
                </h2>
                <p className="text-sm text-slate-500">
                  {finding.resource_type}
                  {finding.line_number ? ` · line ${finding.line_number}` : ""}
                </p>
              </div>
              <button
                onClick={onClose}
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                aria-label="Close panel"
              >
                ✕
              </button>
            </header>

            <nav className="flex gap-1 border-b border-slate-200 px-5 pt-3">
              <TabButton
                active={tab === "explanation"}
                onClick={() => setTab("explanation")}
              >
                Explanation
              </TabButton>
              {showFix && (
                <TabButton active={tab === "fix"} onClick={() => setTab("fix")}>
                  Fix
                </TabButton>
              )}
            </nav>

            <div className="flex-1 overflow-y-auto p-5">
              {tab === "explanation" ? (
                <div className="space-y-4">
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                    {finding.ai_explanation ||
                      "AI explanation is being generated…"}
                  </p>
                  {finding.code_snippet && (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase text-slate-400">
                        Offending code
                      </h3>
                      <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
                        <code>{finding.code_snippet}</code>
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase text-slate-400">
                      Suggested fix
                    </h3>
                    <button
                      onClick={copyFix}
                      className="rounded border border-slate-300 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
                    >
                      {copied ? "Copied!" : "Copy"}
                    </button>
                  </div>
                  <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-green-200">
                    <code>{finding.ai_fix_code}</code>
                  </pre>
                </div>
              )}
            </div>
          </>
        )}
      </aside>
    </>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-t-md px-4 py-2 text-sm font-medium ${
        active
          ? "border-b-2 border-blue-600 text-blue-700"
          : "text-slate-500 hover:text-slate-700"
      }`}
    >
      {children}
    </button>
  );
}
