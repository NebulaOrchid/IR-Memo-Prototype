const SECTIONS = [
  { id: "bio", label: "Background and Analyst Bio" },
  { id: "forecast", label: "Analyst Forecast" },
  { id: "earnings", label: "Post-Earnings Feedback and Questions" },
  { id: "peer", label: "Recent Peer Research" },
  { id: "valuation", label: "Valuation Ratios" },
];

export default function SectionPicker({ selected, onChange, disabled }) {
  const toggle = (id) => {
    if (disabled) return;
    if (selected.includes(id)) {
      onChange(selected.filter((s) => s !== id));
    } else {
      onChange([...selected, id]);
    }
  };

  const allSelected = selected.length === SECTIONS.length;
  const toggleAll = () => {
    if (disabled) return;
    onChange(allSelected ? [] : SECTIONS.map((s) => s.id));
  };

  return (
    <div className="mb-5">
      <label className="block text-sm font-semibold text-gray-700 mb-1.5">
        Sections to Generate
      </label>
      <div className="space-y-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={toggleAll}
            disabled={disabled}
            className="rounded border-gray-300 text-blue-900 focus:ring-blue-900"
          />
          <span className="text-sm font-medium text-gray-800">
            All Sections
          </span>
        </label>
        <div className="ml-4 space-y-1.5">
          {SECTIONS.map((s) => (
            <label
              key={s.id}
              className="flex items-center gap-2 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selected.includes(s.id)}
                onChange={() => toggle(s.id)}
                disabled={disabled}
                className="rounded border-gray-300 text-blue-900 focus:ring-blue-900"
              />
              <span className="text-sm text-gray-700">{s.label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
