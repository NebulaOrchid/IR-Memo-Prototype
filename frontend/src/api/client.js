const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchAnalysts() {
  const res = await fetch(`${API_BASE_URL}/api/analysts`);
  if (!res.ok) throw new Error("Failed to fetch analysts");
  return res.json();
}

/**
 * Safely parse SSE event data. Handles potential double-encoding
 * where sse-starlette may JSON-encode an already-serialized string.
 */
function parseEventData(raw) {
  let parsed = JSON.parse(raw);
  // If sse-starlette double-encoded, parsed will be a string — parse again
  if (typeof parsed === "string") {
    parsed = JSON.parse(parsed);
  }
  return parsed;
}

export function generateMemo(analyst, company, sections, callbacks) {
  const params = new URLSearchParams({
    analyst,
    company,
    sections: sections.join(","),
  });

  const eventSource = new EventSource(
    `${API_BASE_URL}/api/generate?${params.toString()}`
  );

  eventSource.addEventListener("steps", (e) => {
    try {
      const data = parseEventData(e.data);
      console.log("[SSE] steps:", data);
      callbacks.onSteps(data);
    } catch (err) {
      console.error("[SSE] Failed to parse steps event:", err, e.data);
    }
  });

  eventSource.addEventListener("step_update", (e) => {
    try {
      const data = parseEventData(e.data);
      callbacks.onStepUpdate(data);
    } catch (err) {
      console.error("[SSE] Failed to parse step_update event:", err, e.data);
    }
  });

  eventSource.addEventListener("section", (e) => {
    try {
      const data = parseEventData(e.data);
      console.log("[SSE] section:", data.section);
      callbacks.onSection(data);
    } catch (err) {
      console.error("[SSE] Failed to parse section event:", err, e.data);
    }
  });

  eventSource.addEventListener("valuation", (e) => {
    try {
      callbacks.onValuation(parseEventData(e.data));
    } catch (err) {
      console.error("[SSE] Failed to parse valuation event:", err, e.data);
    }
  });

  eventSource.addEventListener("forecast", (e) => {
    try {
      callbacks.onForecast(parseEventData(e.data));
    } catch (err) {
      console.error("[SSE] Failed to parse forecast event:", err, e.data);
    }
  });

  eventSource.addEventListener("quality_check", (e) => {
    try {
      callbacks.onQualityCheck(parseEventData(e.data));
    } catch (err) {
      console.error("[SSE] Failed to parse quality_check event:", err, e.data);
    }
  });

  eventSource.addEventListener("complete", (e) => {
    try {
      console.log("[SSE] complete");
      callbacks.onComplete(parseEventData(e.data));
    } catch (err) {
      console.error("[SSE] Failed to parse complete event:", err, e.data);
    }
    eventSource.close();
  });

  // Backend sends server errors as "server_error" event
  eventSource.addEventListener("server_error", (e) => {
    try {
      const data = parseEventData(e.data);
      console.error("[SSE] Backend error:", data);
      callbacks.onError(data);
    } catch (err) {
      console.error("[SSE] Failed to parse server_error:", err);
      callbacks.onError(e);
    }
    eventSource.close();
  });

  // Native EventSource error — connection lost
  eventSource.onerror = (e) => {
    console.error("[SSE] EventSource connection error:", e);
    callbacks.onError(e);
    eventSource.close();
  };

  return eventSource;
}

/**
 * Regenerate a single memo section via POST SSE stream.
 * Uses fetch + ReadableStream since EventSource only supports GET.
 */
export async function regenerateSection(payload, callbacks) {
  const response = await fetch(`${API_BASE_URL}/api/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    callbacks.onError?.({ message: `HTTP ${response.status}` });
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop(); // keep incomplete line in buffer

    let currentEvent = null;
    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:") && currentEvent) {
        const raw = line.slice(5).trim();
        try {
          const data = parseEventData(raw);
          switch (currentEvent) {
            case "regen_start":
              callbacks.onStart?.(data);
              break;
            case "regen_step":
              callbacks.onStep?.(data);
              break;
            case "regen_section":
              callbacks.onSection?.(data);
              break;
            case "regen_forecast":
              callbacks.onForecast?.(data);
              break;
            case "regen_valuation":
              callbacks.onValuation?.(data);
              break;
            case "regen_complete":
              callbacks.onComplete?.(data);
              break;
            case "regen_error":
              callbacks.onError?.(data);
              break;
          }
        } catch (err) {
          console.error("[Regen SSE] Parse error:", err, raw);
        }
        currentEvent = null;
      } else if (line.trim() === "") {
        currentEvent = null;
      }
    }
  }
}


export function getDownloadUrl(memoId) {
  return `${API_BASE_URL}/api/download/${memoId}`;
}
