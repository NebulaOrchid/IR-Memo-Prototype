export default function ForecastTable({ data }) {
  if (!data || !data.table_rows) return null;

  const { is_stale, table_rows, rating, price_target } = data;

  const formatValue = (val, label) => {
    if (val === null || val === undefined) return "—";
    if (label === "EPS") return `$${Number(val).toFixed(2)}`;
    if (label === "ROE" || label === "ROTCE") return `${Number(val).toFixed(1)}%`;
    return Number(val).toLocaleString();
  };

  return (
    <div>
      {is_stale && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3 py-1.5 rounded mb-3">
          Warning: Forecast data is older than 30 days. Consider requesting updated estimates.
        </div>
      )}

      <div className="overflow-x-auto border border-gray-200 rounded">
        <table className="w-full text-[13px] border-collapse">
          <thead>
            <tr className="bg-[#003366] text-white">
              <th className="text-left px-3 py-2 font-semibold w-[40%]">Metric</th>
              <th className="text-right px-3 py-2 font-semibold w-[20%]">Analyst</th>
              <th className="text-right px-3 py-2 font-semibold w-[20%]">Consensus</th>
              <th className="text-right px-3 py-2 font-semibold w-[20%]">Δ vs Cons.</th>
            </tr>
          </thead>
          <tbody>
            {table_rows.map((row, i) => {
              const isParent = row.indent === 0;
              const isBold = row.bold || isParent;
              const isHighlight = row.highlight;
              const indentPx = row.indent * 18;
              return (
                <tr
                  key={i}
                  className={`border-b border-gray-100 ${
                    isHighlight ? "bg-amber-50" : isParent ? "bg-gray-50" : ""
                  } ${isBold ? "font-semibold" : ""}`}
                >
                  <td
                    className="px-3 py-[5px] text-gray-800"
                    style={{ paddingLeft: `${12 + indentPx}px` }}
                  >
                    {!isParent && <span className="text-gray-300 mr-1 text-xs">›</span>}
                    {row.label}
                  </td>
                  <td className="px-3 py-[5px] text-right text-gray-800 tabular-nums">
                    {formatValue(row.analyst, row.label)}
                  </td>
                  <td className="px-3 py-[5px] text-right text-gray-500 tabular-nums">
                    {formatValue(row.consensus, row.label)}
                  </td>
                  <td className={`px-3 py-[5px] text-right tabular-nums font-medium ${
                    typeof row.delta === "string" && row.delta.startsWith("+")
                      ? "text-green-700"
                      : typeof row.delta === "string" && row.delta.startsWith("-")
                      ? "text-red-600"
                      : "text-gray-500"
                  }`}>
                    {row.delta}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-2.5 flex gap-6 text-sm text-gray-700">
        <span><span className="font-semibold">Rating:</span> {rating || "—"}</span>
        <span><span className="font-semibold">Price Target:</span> {price_target !== null ? `$${price_target}` : "—"}</span>
      </div>
    </div>
  );
}
