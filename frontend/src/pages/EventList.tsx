import { useState, useEffect } from "react";
import { fetchEvents, type Event } from "@/api/client";

export default function EventList() {
  const [events, setEvents] = useState<Event[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);

  useEffect(() => {
    fetchEvents().then(setEvents).catch(() => setEvents([]));
  }, []);

  const filteredEvents = events.filter((event) =>
    event.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (event.topic && event.topic.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const goPrev = () => {
    if (currentPage > 1) setCurrentPage((prev) => prev - 1);
  };

  const goNext = () => {
    const maxPage = Math.ceil(filteredEvents.length / itemsPerPage);
    if (currentPage < maxPage) setCurrentPage((prev) => prev + 1);
  };

  const startIndex = (currentPage - 1) * itemsPerPage;
  const pagedEvents = filteredEvents.slice(startIndex, startIndex + itemsPerPage);
  const totalPages = Math.ceil(filteredEvents.length / itemsPerPage);

  const inputClass = "flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 px-3 py-2 border";
  const btnClass = "px-2 py-1 rounded text-sm text-gray-600 hover:text-gray-900";

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 bg-gray-50 rounded-lg shadow-sm">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Events</h1>
      </div>
      <div className="mb-4 flex gap-2">
        <input
          type="text"
          placeholder="Search events..."
          value={searchQuery}
          onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
          className={inputClass}
        />
        <button
          onClick={() => window.location.reload()}
          className="rounded-md border-gray-300 shadow-sm px-3 py-2 text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 border"
        >
          Refresh
        </button>
      </div>

      {filteredEvents.length === 0 && (
        <div className="text-center py-10 text-gray-500">No events found.</div>
      )}

      {filteredEvents.length > 0 && (
        <>
          <table className="w-full text-sm border-collapse">
            <caption className="text-left text-sm text-gray-500 mb-2">Events</caption>
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 pr-4 font-medium text-gray-700">Event</th>
                <th className="text-left py-2 pr-4 font-medium text-gray-700">Status</th>
                <th className="text-left py-2 pr-4 font-medium text-gray-700">Score</th>
                <th className="text-left py-2 font-medium text-gray-700">Date</th>
              </tr>
            </thead>
            <tbody>
              {pagedEvents.map((event, index) => (
                <tr key={index} className="border-b border-gray-100">
                  <td className="py-2 pr-4">{event.title}</td>
                  <td className="py-2 pr-4">{event.status}</td>
                  <td className="py-2 pr-4">{event.score ?? "—"}</td>
                  <td className="py-2">{event.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex justify-between items-center mt-4">
            <button onClick={goPrev} disabled={currentPage === 1} className={btnClass}>
              Previous
            </button>
            <span className="text-sm text-gray-500">
              Page {currentPage} of {totalPages}
            </span>
            <button onClick={goNext} disabled={currentPage >= totalPages} className={btnClass}>
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
