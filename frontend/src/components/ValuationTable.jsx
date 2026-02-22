const METRICS_ORDER = [
  "Stock Price",
  "P/E (TTM)",
  "Forward P/E",
  "Price/Book",
  "Dividend Yield",
  "Market Cap ($B)",
  "52W High",
  "52W Low",
];

const DEFAULT_TICKER_ORDER = ["MS", "GS", "JPM", "BAC", "C", "WFC", "SCHW"];

export default function ValuationTable({ data }) {
  if (!data || !data.tickers) return null;

  const { tickers, peer_median } = data;
  // Use dynamic ticker_order from backend if available, else fall back to defaults
  const TICKER_ORDER = data.ticker_order || DEFAULT_TICKER_ORDER;

  const formatVal = (val, metric) => {
    if (val === null || val === undefined) return "—";
    if (val === "-") return "—";
    if (metric === "Stock Price" || metric === "52W High" || metric === "52W Low")
      return `$${Number(val).toFixed(2)}`;
    if (metric === "Dividend Yield") return `${Number(val).toFixed(2)}%`;
    if (metric === "Market Cap ($B)") return Number(val).toFixed(1);
    return Number(val).toFixed(2);
  };

  return (
    <div className="overflow-x-auto border border-gray-200 rounded">
      <table className="w-full text-[13px] border-collapse">
        <thead>
          <tr className="bg-[#003366] text-white">
            <th className="text-left px-2 py-2 font-semibold">Metric</th>
            {TICKER_ORDER.map((t) => (
              <th
                key={t}
                className={`text-right px-2 py-2 font-semibold ${
                  t === "MS" ? "bg-[#004488]" : ""
                }`}
              >
                {t}
              </th>
            ))}
            <th className="text-right px-2 py-2 font-semibold bg-[#1a4d80]">
              Peer Med.
            </th>
          </tr>
        </thead>
        <tbody>
          {METRICS_ORDER.map((metric, idx) => (
            <tr
              key={metric}
              className={`border-b border-gray-100 ${
                idx % 2 === 0 ? "bg-white" : "bg-gray-50/50"
              }`}
            >
              <td className="px-2 py-[5px] font-medium text-gray-800">{metric}</td>
              {TICKER_ORDER.map((ticker) => (
                <td
                  key={ticker}
                  className={`px-2 py-[5px] text-right tabular-nums ${
                    ticker === "MS"
                      ? "font-semibold text-[#003366] bg-blue-50/40"
                      : "text-gray-700"
                  }`}
                >
                  {formatVal(tickers[ticker]?.[metric], metric)}
                </td>
              ))}
              <td className="px-2 py-[5px] text-right tabular-nums font-medium text-gray-800 bg-gray-50">
                {formatVal(peer_median?.[metric], metric)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
