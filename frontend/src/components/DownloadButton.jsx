import { getDownloadUrl } from "../api/client";

export default function DownloadButton({ memoId }) {
  if (!memoId) return null;

  return (
    <button
      onClick={() => window.open(getDownloadUrl(memoId), "_blank")}
      className="w-full bg-[#003366] hover:bg-[#002244] text-white font-semibold py-2.5 px-4 rounded-md transition-colors flex items-center justify-center gap-2"
    >
      <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
      </svg>
      Download Word Document
    </button>
  );
}
