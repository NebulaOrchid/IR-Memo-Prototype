import { useEffect, useState } from "react";
import { fetchAnalysts } from "../api/client";

export default function AnalystSelector({ value, onChange, disabled }) {
  const [analysts, setAnalysts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalysts()
      .then((data) => {
        setAnalysts(data);
        if (data.length > 0 && !value) {
          onChange(data[0].name);
        }
      })
      .catch(() => {
        // Fallback if backend is not running
        setAnalysts([{ name: "Mike Mayo", firm: "Wells Fargo Securities" }]);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mb-5">
      <label className="block text-sm font-semibold text-gray-700 mb-1.5">
        Select Analyst
      </label>
      <select
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || loading}
        className="w-full border border-gray-300 rounded-md px-3 py-2.5 text-sm bg-white focus:ring-2 focus:ring-blue-900 focus:border-blue-900 outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
      >
        <option value="">Choose analyst...</option>
        {analysts.map((a) => (
          <option key={a.name} value={a.name}>
            {a.name} — {a.firm}
          </option>
        ))}
      </select>
    </div>
  );
}
