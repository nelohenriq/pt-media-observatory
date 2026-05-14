import { useState } from "react";

interface ReviewItem {
  id: string;
  title: string;
  status: string;
  score?: number;
}

export default function ReviewPanel() {
  const [items, setItems] = useState<ReviewItem[]>([]);

  const approve = (id: string) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, status: "approved" } : item
      )
    );
  };

  const reject = (id: string) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, status: "rejected" } : item
      )
    );
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 bg-gray-50 rounded-lg shadow-sm">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Review Panel</h1>
      {items.length === 0 && (
        <div className="text-center py-10 text-gray-500">No items pending review.</div>
      )}
      <ul className="space-y-4">
        {items.map((item) => (
          <li
            key={item.id}
            className={`p-4 bg-white rounded-lg shadow-sm border-l-4 ${
              item.status === "approved" ? "border-green-500" :
              item.status === "rejected" ? "border-red-500" : "border-yellow-400"
            }`}
          >
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-medium text-gray-900">{item.title}</h3>
                <span className="text-sm text-gray-500">
                  {item.status} — score: {item.score ?? "—"}
                </span>
              </div>
              {item.status === "pending" && (
                <div className="flex gap-2">
                  <button
                    onClick={() => approve(item.id)}
                    className="px-3 py-1 text-sm font-medium text-white bg-green-600 rounded hover:bg-green-700"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => reject(item.id)}
                    className="px-3 py-1 text-sm font-medium text-white bg-red-600 rounded hover:bg-red-700"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
