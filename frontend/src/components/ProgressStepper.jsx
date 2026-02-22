import { useState, useEffect, useRef } from "react";

/**
 * Hierarchical progress stepper with rich findings preview.
 *
 * Props:
 *   steps: [{ id, label, children: [{ id, label, status, findings }] }]
 *
 * findings can be:
 *   - a string (backward compat)
 *   - an object: { summary, sources?: [{url, domain, label}], detail? }
 */
export default function ProgressStepper({ steps, elapsedSeconds, isGenerating }) {
  const [expandedStepId, setExpandedStepId] = useState(null);
  const prevRunningRef = useRef(null);

  // Auto-expand findings on complete, auto-collapse when next step starts
  useEffect(() => {
    let currentRunning = null;
    let latestCompleteWithFindings = null;

    for (const group of steps) {
      for (const child of group.children) {
        if (child.status === "running") {
          currentRunning = child.id;
        }
        if (child.status === "complete" && child.findings) {
          latestCompleteWithFindings = child.id;
        }
      }
    }

    // If a new step started running, collapse previous findings
    if (currentRunning && currentRunning !== prevRunningRef.current) {
      setExpandedStepId(null);
      prevRunningRef.current = currentRunning;
      return;
    }

    // If a step just completed (was previously running), expand its findings
    if (
      prevRunningRef.current &&
      latestCompleteWithFindings === prevRunningRef.current
    ) {
      setExpandedStepId(latestCompleteWithFindings);
      prevRunningRef.current = null;
      return;
    }

    // If nothing is running and we have completed steps, show the latest
    if (!currentRunning && latestCompleteWithFindings && !expandedStepId) {
      setExpandedStepId(latestCompleteWithFindings);
    }
  }, [steps]);

  if (!steps || steps.length === 0) return null;

  const toggleFindings = (childId) => {
    setExpandedStepId((prev) => (prev === childId ? null : childId));
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          Agent Progress
        </h3>
        {elapsedSeconds > 0 && (
          <span className={`text-xs tabular-nums ${isGenerating ? "text-blue-600" : "text-gray-400"}`}>
            {isGenerating && (
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse mr-1.5 align-middle" />
            )}
            Elapsed: {formatElapsed(elapsedSeconds)}
          </span>
        )}
      </div>
      <div className="space-y-1">
        {steps.map((group, groupIdx) => (
          <StepGroup
            key={group.id}
            group={group}
            isLast={groupIdx === steps.length - 1}
            expandedStepId={expandedStepId}
            onToggleFindings={toggleFindings}
          />
        ))}
      </div>
    </div>
  );
}


function getGroupStatus(children) {
  if (!children || children.length === 0) return "pending";
  const statuses = children.map((c) => c.status);
  if (statuses.some((s) => s === "running")) return "running";
  if (statuses.every((s) => s === "complete")) return "complete";
  if (statuses.some((s) => s === "error") && !statuses.some((s) => s === "running")) return "error";
  if (statuses.some((s) => s === "complete")) return "running"; // partially done
  return "pending";
}


function StepGroup({ group, isLast, expandedStepId, onToggleFindings }) {
  const groupStatus = getGroupStatus(group.children);

  return (
    <div className={`${!isLast ? "mb-2" : ""}`}>
      {/* Parent row */}
      <div className="flex items-center gap-3 py-1.5">
        <GroupIcon status={groupStatus} />
        <span
          className={`text-sm font-semibold ${
            groupStatus === "running"
              ? "text-blue-900"
              : groupStatus === "complete"
              ? "text-green-800"
              : groupStatus === "error"
              ? "text-red-700"
              : "text-gray-400"
          }`}
        >
          {group.label}
        </span>
      </div>

      {/* Children (indented) */}
      <div className="ml-4 border-l-2 border-gray-100 pl-4">
        {group.children.map((child) => (
          <div key={child.id}>
            <div
              className={`flex items-center gap-2.5 py-1 ${
                child.status === "complete" && child.findings ? "cursor-pointer" : ""
              }`}
              onClick={() => {
                if (child.status === "complete" && child.findings) {
                  onToggleFindings(child.id);
                }
              }}
            >
              <ChildIcon status={child.status} />
              <span
                className={`text-xs ${
                  child.status === "running"
                    ? "font-medium text-blue-800"
                    : child.status === "complete"
                    ? "text-gray-500"
                    : child.status === "error"
                    ? "text-red-500"
                    : "text-gray-300"
                }`}
              >
                {child.label}
              </span>
              {child.status === "complete" && child.findings && (
                <svg
                  className={`w-3 h-3 text-gray-400 transition-transform ${
                    expandedStepId === child.id ? "rotate-90" : ""
                  }`}
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>

            {/* Findings preview (rich or simple) */}
            {expandedStepId === child.id && child.findings && (
              <FindingsPreview findings={child.findings} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}


/** Render structured findings with sources, or fallback to plain string. */
function FindingsPreview({ findings }) {
  // Plain string (backward compat)
  if (typeof findings === "string") {
    return (
      <div className="ml-7 mb-1.5 py-1.5 px-3 bg-gray-50 border border-gray-100 rounded text-xs text-gray-600 leading-relaxed">
        {findings}
      </div>
    );
  }

  // Structured findings object
  const { summary, sources, detail, preview } = findings;

  return (
    <div className="ml-7 mb-1.5 py-2 px-3 bg-gray-50 border border-gray-100 rounded text-xs leading-relaxed">
      {/* Summary line */}
      {summary && (
        <div className="text-gray-700 font-medium">{summary}</div>
      )}

      {/* Source list */}
      {sources && sources.length > 0 && (
        <div className="mt-1.5">
          <span className="text-gray-400 font-medium text-[10px] uppercase tracking-wider">Sources:</span>
          <div className="mt-0.5 space-y-0.5">
            {sources.map((src, i) => (
              <div key={i} className="flex items-start gap-1.5 text-gray-500">
                <span className="shrink-0 text-gray-300 mt-px">&#8226;</span>
                <span>
                  <span className="text-gray-600">{src.domain}</span>
                  {src.label && src.label !== src.domain && (
                    <span className="text-gray-400 ml-1">({truncate(src.label, 60)})</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detail line */}
      {detail && (
        <div className="mt-1 text-gray-400 italic">{detail}</div>
      )}

      {/* Preview panel for local sources */}
      {preview && <SourcePreview preview={preview} />}
    </div>
  );
}


/** Renders an expandable source preview for local file data. */
function SourcePreview({ preview }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-2 border border-gray-200 rounded bg-white">
      {/* Toggle header */}
      <button
        onClick={(e) => { e.stopPropagation(); setExpanded((v) => !v); }}
        className="w-full flex items-center justify-between px-2.5 py-1.5 text-[11px] text-gray-500 hover:bg-gray-50 transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <svg className="w-3 h-3 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
            <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
          </svg>
          <span className="font-medium">View Source</span>
        </span>
        <svg
          className={`w-3 h-3 text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>

      {expanded && (
        <div className="px-2.5 pb-2.5 border-t border-gray-100">
          {preview.type === "forecast_table" && <ForecastPreviewTable rows={preview.rows} />}
          {preview.type === "transcript_snippet" && (
            <TranscriptSnippet
              snippet={preview.snippet}
              analystName={preview.analyst_name}
              charCount={preview.char_count}
            />
          )}

          {/* Local source label */}
          {preview.local_source && (
            <div className="mt-2 flex items-center gap-1.5 text-[10px] text-amber-600">
              <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span>Local source &mdash; connects to SharePoint / API in production</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


/** Compact key-value table for forecast Excel preview. */
function ForecastPreviewTable({ rows }) {
  if (!rows || rows.length === 0) return null;
  return (
    <table className="w-full mt-1.5 text-[11px]">
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className={i % 2 === 0 ? "bg-gray-50/50" : ""}>
            <td className="py-1 px-2 text-gray-400 font-medium w-1/3">{row.label}</td>
            <td className="py-1 px-2 text-gray-700">{row.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}


/** Transcript snippet with analyst name highlighted. */
function TranscriptSnippet({ snippet, analystName, charCount }) {
  if (!snippet) return null;

  // Highlight the analyst name in the snippet
  const lastName = analystName?.split(" ").pop() || "";
  const parts = snippet.split(new RegExp(`(${escapeRegex(analystName)}|${escapeRegex(lastName)}:)`, "gi"));

  return (
    <div className="mt-1.5">
      <pre className="whitespace-pre-wrap text-[11px] text-gray-600 leading-relaxed font-mono bg-slate-50 rounded p-2 border border-slate-100 max-h-36 overflow-y-auto">
        {parts.map((part, i) =>
          part.toLowerCase().includes(lastName.toLowerCase()) ? (
            <span key={i} className="bg-amber-100 text-amber-800 font-semibold">{part}</span>
          ) : (
            <span key={i}>{part}</span>
          )
        )}
      </pre>
      {charCount && (
        <div className="mt-1 text-[10px] text-gray-400">
          Showing first question &middot; Full transcript: {charCount.toLocaleString()} characters
        </div>
      )}
    </div>
  );
}


function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}


function formatElapsed(seconds) {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}


function truncate(str, max) {
  if (!str) return "";
  return str.length > max ? str.slice(0, max) + "..." : str;
}


function GroupIcon({ status }) {
  const base = "w-6 h-6 rounded-full flex items-center justify-center shrink-0";

  switch (status) {
    case "running":
      return (
        <div className={`${base} bg-blue-900 text-white`}>
          <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="60" strokeDashoffset="20" />
          </svg>
        </div>
      );
    case "complete":
      return (
        <div className={`${base} bg-green-600 text-white`}>
          <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        </div>
      );
    case "error":
      return (
        <div className={`${base} bg-red-500 text-white`}>
          <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </div>
      );
    default:
      return (
        <div className={`${base} bg-gray-200`}>
          <div className="w-2 h-2 rounded-full bg-gray-400" />
        </div>
      );
  }
}


function ChildIcon({ status }) {
  const base = "w-4 h-4 rounded-full flex items-center justify-center shrink-0";

  switch (status) {
    case "running":
      return (
        <div className={`${base} border-2 border-blue-500`}>
          <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
        </div>
      );
    case "complete":
      return (
        <div className={`${base} bg-green-500 text-white`}>
          <svg className="w-2.5 h-2.5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        </div>
      );
    case "error":
      return (
        <div className={`${base} bg-red-400 text-white`}>
          <svg className="w-2.5 h-2.5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </div>
      );
    default:
      return (
        <div className={`${base} border border-gray-300`}>
          <div className="w-1 h-1 rounded-full bg-gray-300" />
        </div>
      );
  }
}
