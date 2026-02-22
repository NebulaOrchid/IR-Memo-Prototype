import { useState, useCallback, useRef, useEffect } from "react";
import { generateMemo, regenerateSection } from "./api/client";
import AnalystSelector from "./components/AnalystSelector";
import SectionPicker from "./components/SectionPicker";
import ProgressStepper from "./components/ProgressStepper";
import MemoDisplay from "./components/MemoDisplay";
import DownloadButton from "./components/DownloadButton";

const ALL_SECTIONS = ["bio", "forecast", "earnings", "peer", "valuation"];

export default function App() {
  const [analyst, setAnalyst] = useState("");
  const [selectedSections, setSelectedSections] = useState([...ALL_SECTIONS]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [steps, setSteps] = useState([]);
  const [memo, setMemo] = useState(null);
  const [qualityCheck, setQualityCheck] = useState(null);
  const [memoId, setMemoId] = useState(null);
  const [error, setError] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [generationStats, setGenerationStats] = useState(null);
  const [regeneratingSection, setRegeneratingSection] = useState(null);

  const timerRef = useRef(null);
  const startTimeRef = useRef(null);
  // Store the current memo object mutably for callbacks
  const currentMemoRef = useRef(null);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const startTimer = () => {
    startTimeRef.current = Date.now();
    setElapsedSeconds(0);
    setGenerationStats(null);
    timerRef.current = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
  };

  const stopTimer = (currentMemo) => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    const finalElapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
    setElapsedSeconds(finalElapsed);

    // Compute stats from completed sections
    const sections = currentMemo.sections || {};
    const sectionCount = Object.keys(sections).length;
    let liveSources = 0;
    let localSources = 0;
    const LIVE_KEYS = new Set(["bio", "peer", "valuation"]);
    const LOCAL_KEYS = new Set(["forecast"]);
    for (const [key, sec] of Object.entries(sections)) {
      if (LIVE_KEYS.has(key)) {
        liveSources++;
      } else if (LOCAL_KEYS.has(key)) {
        localSources++;
      } else {
        const srcs = sec.sources || [];
        const hasLive = srcs.some((s) => s.url);
        if (hasLive) liveSources++;
        else localSources++;
      }
    }
    setGenerationStats({ elapsed: finalElapsed, sectionCount, liveSources, localSources });
  };

  const handleGenerate = useCallback(() => {
    if (!analyst || selectedSections.length === 0) return;

    // Reset state
    setIsGenerating(true);
    setSteps([]);
    setMemo(null);
    setQualityCheck(null);
    setMemoId(null);
    setError(null);
    setRegeneratingSection(null);
    startTimer();

    const currentMemo = { analyst: "", firm: "", date: "", sections: {} };
    currentMemoRef.current = currentMemo;

    generateMemo(analyst, "MS", selectedSections, {
      onSteps: ({ steps: newSteps }) => {
        setSteps(
          newSteps.map((group) => ({
            ...group,
            children: group.children.map((child) => ({
              ...child,
              status: "pending",
              findings: null,
            })),
          }))
        );
      },

      onStepUpdate: ({ step, status, findings }) => {
        setSteps((prev) =>
          prev.map((group) => ({
            ...group,
            children: group.children.map((child) =>
              child.id === step
                ? { ...child, status, findings: findings || child.findings }
                : child
            ),
          }))
        );
      },

      onSection: ({ section, content, sources, confidence }) => {
        currentMemo.sections[section] = { content, status: "success", sources, confidence };
        setMemo({ ...currentMemo });
      },

      onForecast: (forecastData) => {
        currentMemo.analyst = forecastData.analyst_name || analyst;
        currentMemo.firm = forecastData.firm || "";
        currentMemo.sections.forecast = forecastData;
        setMemo({ ...currentMemo });
      },

      onValuation: (valuationData) => {
        currentMemo.sections.valuation = valuationData;
        setMemo({ ...currentMemo });
      },

      onQualityCheck: (qcData) => {
        setQualityCheck(qcData);
      },

      onComplete: ({ memo_id }) => {
        stopTimer(currentMemo);
        setMemoId(memo_id);
        setIsGenerating(false);
        currentMemo.date = new Date().toLocaleDateString("en-US", {
          year: "numeric",
          month: "long",
          day: "numeric",
        });
        if (!currentMemo.analyst) currentMemo.analyst = analyst;
        setMemo({ ...currentMemo });
      },

      onError: () => {
        if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
        setError("Connection to the agent was lost. Please try again.");
        setIsGenerating(false);
      },
    });
  }, [analyst, selectedSections]);

  const handleRegenerate = useCallback((sectionKey, instruction, reSearch, onStepUpdate) => {
    if (!memoId || !analyst) return;

    setRegeneratingSection(sectionKey);

    // Extract current displayed content for the section
    const sectionData = memo?.sections?.[sectionKey] || {};
    const currentContent = sectionData.content || "";

    regenerateSection(
      {
        section: sectionKey,
        analyst,
        instruction: instruction || "",
        re_search: reSearch,
        original_data: {},
        memo_id: memoId,
        current_content: currentContent,
      },
      {
        onStart: () => {
          onStepUpdate?.("Starting regeneration...");
        },
        onStep: (data) => {
          onStepUpdate?.(data.step || "Processing...");
        },
        onSection: (data) => {
          // Update the memo with new section content
          setMemo((prev) => {
            if (!prev) return prev;
            const updated = { ...prev, sections: { ...prev.sections } };
            updated.sections[data.section] = {
              ...updated.sections[data.section],
              content: data.content,
              sources: data.sources,
              confidence: data.confidence,
            };
            if (currentMemoRef.current) {
              currentMemoRef.current.sections[data.section] = updated.sections[data.section];
            }
            return updated;
          });
        },
        onForecast: (data) => {
          setMemo((prev) => {
            if (!prev) return prev;
            const updated = { ...prev, sections: { ...prev.sections } };
            updated.sections.forecast = data;
            if (currentMemoRef.current) {
              currentMemoRef.current.sections.forecast = data;
            }
            return updated;
          });
        },
        onValuation: (data) => {
          setMemo((prev) => {
            if (!prev) return prev;
            const updated = { ...prev, sections: { ...prev.sections } };
            updated.sections.valuation = data;
            if (currentMemoRef.current) {
              currentMemoRef.current.sections.valuation = data;
            }
            return updated;
          });
        },
        onComplete: () => {
          setRegeneratingSection(null);
        },
        onError: (data) => {
          console.error("[Regen] Error:", data);
          setRegeneratingSection(null);
        },
      }
    );
  }, [memoId, analyst, memo]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-[#003366] text-white py-4 px-6 shadow-md">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-xl font-bold tracking-tight">
            IR Briefing Memo Agent
          </h1>
          <p className="text-blue-200 text-sm mt-0.5">
            Automated IR 1-Pager Generation
          </p>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
          {/* Left sidebar: Controls */}
          <div>
            <div className="bg-white border border-gray-200 rounded-lg p-5 sticky top-6">
              <AnalystSelector
                value={analyst}
                onChange={setAnalyst}
                disabled={isGenerating}
              />

              <SectionPicker
                selected={selectedSections}
                onChange={setSelectedSections}
                disabled={isGenerating}
              />

              <button
                onClick={handleGenerate}
                disabled={isGenerating || !analyst || selectedSections.length === 0}
                className="w-full bg-[#003366] hover:bg-[#002244] disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-2.5 px-4 rounded-md transition-colors"
              >
                {isGenerating ? "Generating..." : "Generate Briefing Memo"}
              </button>

              {memoId && (
                <div className="mt-4">
                  <DownloadButton memoId={memoId} />
                </div>
              )}
            </div>
          </div>

          {/* Right panel: Progress + Memo */}
          <div>
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg mb-4 text-sm">
                {error}
              </div>
            )}

            {steps.length > 0 && (
              <ProgressStepper
                steps={steps}
                elapsedSeconds={elapsedSeconds}
                isGenerating={isGenerating}
              />
            )}

            {memo && memo.sections && Object.keys(memo.sections).length > 0 && (
              <MemoDisplay
                memo={memo}
                qualityCheck={qualityCheck}
                generationStats={generationStats}
                onRegenerate={!isGenerating ? handleRegenerate : undefined}
                regeneratingSection={regeneratingSection}
              />
            )}

            {!isGenerating && !memo && (
              <div className="bg-white border border-gray-200 rounded-lg p-12 text-center text-gray-400">
                <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-lg font-medium text-gray-500">
                  Select an analyst and click Generate
                </p>
                <p className="text-sm mt-1">
                  The agent will autonomously research and draft your IR 1-Pager
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
