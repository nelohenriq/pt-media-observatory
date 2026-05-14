import { useState } from "react";

interface Publication {
  id: string;
  title: string;
  status: string;
  publishedAt?: string;
}

export default function PublicationTracker() {
  const [publications] = useState<Publication[]>([]);
  const [search, setSearch] = useState("");

  const filtered = publications.filter((p) =>
    p.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 bg-gray-50 rounded-lg shadow-sm">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Publication Tracker</h1>
      <input
        type="text"
        placeholder="Search publications..."
        value={search}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)}
        className="mb-4 w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 px-3 py-2 border"
      />
      {filtered.length === 0 && (
        <div className="text-center py-10 text-gray-500">No publications found.</div>
      )}
      <ul className="space-y-2">
        {filtered.map((pub) => (
          <li key={pub.id} className="p-3 bg-white rounded shadow-sm flex justify-between">
            <span className="font-medium text-gray-900">{pub.title}</span>
            <span className="text-sm text-gray-500">
              {pub.status}{pub.publishedAt ? ` · ${pub.publishedAt}` : ""}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
