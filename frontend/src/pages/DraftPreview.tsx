import { useState, useEffect } from "react";

interface Draft {
  id: string;
  title: string;
  content: string;
  status: string;
  createdAt: string;
}

export default function DraftPreview() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    // In production this would call the backend /events or /drafts endpoint
    setDrafts([]);
    setLoading(false);
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 bg-gray-50 rounded-lg shadow-sm">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Draft Previews</h1>
      {loading && <div className="text-gray-500">Loading...</div>}
      {drafts.length === 0 && !loading && (
        <div className="text-center py-10 text-gray-500">No drafts yet.</div>
      )}
      {drafts.map((draft) => (
        <div key={draft.id} className="mb-4 p-4 bg-white rounded-lg shadow-sm">
          <h3 className="font-medium text-gray-900">{draft.title}</h3>
          <p className="text-sm text-gray-600 mt-1">{draft.content}</p>
          <div className="mt-2 text-xs text-gray-400">
            {draft.status} · {draft.createdAt}
          </div>
        </div>
      ))}
    </div>
  );
}
