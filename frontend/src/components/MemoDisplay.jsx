import { useState, useRef, useEffect } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ForecastTable from "./ForecastTable";
import ValuationTable from "./ValuationTable";

export default function MemoDisplay({ memo, qualityCheck, generationStats, onRegenerate, regeneratingSection }) {
  if (!memo || Object.keys(memo).length === 0) return null;

  const { analyst, firm, date, sections } = memo;

  return (
    <div className="space-y-4">
      {/* Title Card */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <div className="bg-[#003366] px-6 py-4">
          <h1 className="text-lg font-bold text-white text-center tracking-tight">
            IR 1-Pager: {analyst} ({firm})
          </h1>
          <p className="text-blue-200 text-xs text-center mt-1">
            Prepared {date} — Confidential: For Internal Use Only
          </p>
        </div>
      </div>

      {/* Section 1: Bio */}
      {sections.bio && (
        <SectionCard
          title="Background and Analyst Bio"
          sectionKey="bio"
          qualityCheck={qualityCheck}
          sources={sections.bio.sources}
          confidence={sections.bio.confidence}
          onRegenerate={onRegenerate}
          isRegenerating={regeneratingSection === "bio"}
        >
          <div className="memo-prose text-sm leading-relaxed text-gray-800">
            <Markdown remarkPlugins={[remarkGfm]}>{sections.bio.content || sections.bio}</Markdown>
          </div>
        </SectionCard>
      )}

      {/* Section 2: Forecast */}
      {sections.forecast && sections.forecast.table_rows && (
        <SectionCard
          title={`${sections.forecast.analyst_name || analyst}'s Forecast (As of ${sections.forecast.date_updated || "N/A"})`}
          sectionKey="forecast"
          qualityCheck={qualityCheck}
          sources={sections.forecast.sources}
          confidence={sections.forecast.confidence}
          onRegenerate={onRegenerate}
          isRegenerating={regeneratingSection === "forecast"}
        >
          <ForecastTable data={sections.forecast} />
        </SectionCard>
      )}

      {/* Section 3: Earnings */}
      {sections.earnings && (
        <SectionCard
          title="Post-Earnings Feedback and Questions"
          sectionKey="earnings"
          qualityCheck={qualityCheck}
          sources={sections.earnings.sources}
          confidence={sections.earnings.confidence}
          onRegenerate={onRegenerate}
          isRegenerating={regeneratingSection === "earnings"}
        >
          <div className="memo-prose text-sm leading-relaxed text-gray-800">
            <Markdown remarkPlugins={[remarkGfm]}>{sections.earnings.content || sections.earnings}</Markdown>
          </div>
        </SectionCard>
      )}

      {/* Section 4: Peer Research */}
      {sections.peer && (
        <SectionCard
          title="Recent Peer Research"
          sectionKey="peer"
          qualityCheck={qualityCheck}
          sources={sections.peer.sources}
          confidence={sections.peer.confidence}
          onRegenerate={onRegenerate}
          isRegenerating={regeneratingSection === "peer"}
        >
          <div className="memo-prose text-sm leading-relaxed text-gray-800">
            <Markdown remarkPlugins={[remarkGfm]}>{sections.peer.content || sections.peer}</Markdown>
          </div>
        </SectionCard>
      )}

      {/* Section 5: Valuation */}
      {sections.valuation && sections.valuation.tickers && (
        <SectionCard
          title={`Valuation Ratios (As of ${sections.valuation.as_of || "N/A"})`}
          sectionKey="valuation"
          qualityCheck={qualityCheck}
          sources={sections.valuation.sources}
          confidence={sections.valuation.confidence}
          onRegenerate={onRegenerate}
          isRegenerating={regeneratingSection === "valuation"}
        >
          <ValuationTable data={sections.valuation} />
        </SectionCard>
      )}

      {/* Quality Check Summary */}
      {qualityCheck && (
        <div className={`rounded-lg border px-5 py-3 text-sm ${
          qualityCheck.overall_status === "pass"
            ? "bg-green-50 border-green-200 text-green-800"
            : qualityCheck.overall_status === "fail"
            ? "bg-red-50 border-red-200 text-red-800"
            : "bg-amber-50 border-amber-200 text-amber-800"
        }`}>
          <span className="font-semibold">Quality Check:</span> {qualityCheck.summary}
        </div>
      )}

      {/* Generation Summary Bar */}
      {generationStats && <GenerationSummary stats={generationStats} />}
    </div>
  );
}


function ConfidenceBadge({ confidence }) {
  if (!confidence) return null;

  const colors = {
    high: "bg-green-100 text-green-700 border-green-200",
    medium: "bg-amber-50 text-amber-700 border-amber-200",
    low: "bg-red-50 text-red-600 border-red-200",
  };

  const icons = {
    high: (
      <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
    ),
    medium: (
      <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
    ),
    low: (
      <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
    ),
  };

  const level = confidence.level || "medium";

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-semibold uppercase tracking-wider ${colors[level] || colors.medium}`}
      title={confidence.reason}
    >
      {icons[level]}
      {level}
    </span>
  );
}


function RegeneratedBadge() {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-semibold uppercase tracking-wider bg-blue-50 text-blue-600 border-blue-200">
      <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
      </svg>
      Regenerated
    </span>
  );
}


function SourcesFooter({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="border-t border-gray-100 px-5 py-2.5 flex items-start gap-2">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 shrink-0 mt-px">
        Sources
      </span>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {sources.map((src, i) => (
          <span key={i} className="text-[11px] text-gray-500">
            {src.url ? (
              <a
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#003366] hover:underline"
                title={src.label}
              >
                {src.domain}
              </a>
            ) : (
              <span title={src.label}>{src.domain}</span>
            )}
            {i < sources.length - 1 && <span className="text-gray-300 ml-1">|</span>}
          </span>
        ))}
      </div>
    </div>
  );
}


function GenerationSummary({ stats }) {
  const { elapsed, sectionCount, liveSources, localSources } = stats;
  const parts = [`${sectionCount} section${sectionCount !== 1 ? "s" : ""}`];
  if (liveSources > 0) parts.push(`${liveSources} live data source${liveSources !== 1 ? "s" : ""}`);
  if (localSources > 0) parts.push(`${localSources} local source${localSources !== 1 ? "s" : ""}`);

  return (
    <div className="bg-green-50 border border-green-200 rounded-lg px-5 py-3 flex items-center gap-2 text-sm text-green-800">
      <svg className="w-4 h-4 text-green-600 shrink-0" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
      <span>
        Memo generated in <span className="font-semibold">{elapsed} seconds</span>
        <span className="text-green-600 mx-1.5">|</span>
        {parts.join(" | ")}
      </span>
    </div>
  );
}


function SectionCard({ title, sectionKey, qualityCheck, sources, confidence, onRegenerate, isRegenerating, children }) {
  const [showPanel, setShowPanel] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [reSearch, setReSearch] = useState(false);
  const [wasRegenerated, setWasRegenerated] = useState(false);
  const [regenStep, setRegenStep] = useState("");
  const [highlight, setHighlight] = useState(false);
  const inputRef = useRef(null);

  const issues = qualityCheck?.sections?.[sectionKey];
  const hasWarning =
    issues && (issues.status === "warning" || issues.status === "fail") && issues.issues?.length > 0;

  // Focus input when panel opens
  useEffect(() => {
    if (showPanel && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showPanel]);

  // Flash highlight animation when regeneration completes
  useEffect(() => {
    if (!isRegenerating && wasRegenerated) {
      setHighlight(true);
      const timer = setTimeout(() => setHighlight(false), 1500);
      return () => clearTimeout(timer);
    }
  }, [isRegenerating, wasRegenerated]);

  const handleRegenerate = () => {
    setShowPanel(false);
    setWasRegenerated(true);
    setRegenStep("");
    onRegenerate?.(sectionKey, instruction, reSearch, (stepLabel) => {
      setRegenStep(stepLabel);
    });
    setInstruction("");
    setReSearch(false);
  };

  const handleCancel = () => {
    setShowPanel(false);
    setInstruction("");
    setReSearch(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleRegenerate();
    } else if (e.key === "Escape") {
      handleCancel();
    }
  };

  return (
    <div className={`bg-white border rounded-lg shadow-sm overflow-hidden relative transition-colors duration-700 ${
      highlight ? "border-blue-400 ring-2 ring-blue-100" : "border-gray-200"
    }`}>
      {/* Spinner overlay during regeneration */}
      {isRegenerating && (
        <div className="absolute inset-0 bg-white/80 z-10 flex flex-col items-center justify-center gap-3">
          <svg className="w-6 h-6 text-[#003366] animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="text-sm text-gray-600 font-medium">
            {regenStep || "Regenerating..."}
          </span>
        </div>
      )}

      {/* Section header with confidence badge + regenerate button */}
      <div className="border-b border-gray-200 bg-gray-50 px-5 py-2.5 flex items-center justify-between">
        <h2 className="text-sm font-bold text-[#003366] uppercase tracking-wide">
          {title}
        </h2>
        <div className="flex items-center gap-2">
          {wasRegenerated && !isRegenerating && <RegeneratedBadge />}
          <ConfidenceBadge confidence={confidence} />
          {onRegenerate && !isRegenerating && (
            <button
              onClick={() => setShowPanel(!showPanel)}
              className="p-1 text-gray-400 hover:text-[#003366] hover:bg-gray-100 rounded transition-colors"
              title="Regenerate section"
            >
              <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Regenerate inline panel */}
      {showPanel && (
        <div className="border-b border-gray-200 bg-blue-50/50 px-5 py-3">
          <div className="flex gap-2 items-start">
            <input
              ref={inputRef}
              type="text"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="What should be different?"
              className="flex-1 text-sm border border-gray-300 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#003366]/30 focus:border-[#003366] placeholder-gray-400"
            />
            <button
              onClick={handleRegenerate}
              className="text-sm bg-[#003366] hover:bg-[#002244] text-white font-medium px-3 py-1.5 rounded-md transition-colors shrink-0"
            >
              Regenerate
            </button>
            <button
              onClick={handleCancel}
              className="text-sm text-gray-500 hover:text-gray-700 px-2 py-1.5 transition-colors shrink-0"
            >
              Cancel
            </button>
          </div>
          <label className="flex items-center gap-2 mt-2 text-xs text-gray-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={reSearch}
              onChange={(e) => setReSearch(e.target.checked)}
              className="rounded border-gray-300 text-[#003366] focus:ring-[#003366]/30"
            />
            Re-search sources
          </label>
        </div>
      )}

      {/* QC warnings */}
      {hasWarning && (
        <div className="bg-amber-50 border-b border-amber-200 text-amber-800 text-xs px-5 py-2">
          {issues.issues.map((issue, i) => (
            <div key={i} className="flex gap-1.5 items-start">
              <span className="shrink-0">&#9888;</span>
              <span>{issue}</span>
            </div>
          ))}
        </div>
      )}

      {/* Section content */}
      <div className="px-5 py-4">
        {children}
      </div>

      {/* Sources footer */}
      <SourcesFooter sources={sources} />
    </div>
  );
}
