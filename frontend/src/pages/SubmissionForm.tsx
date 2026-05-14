import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { submitEvent } from "@/api/client";

export default function SubmissionForm() {
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [topicHints, setTopicHints] = useState("");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");
    try {
      await submitEvent({ url, text, topicHints, notes });
      navigate("/events");
    } catch {
      setError("Submission failed. Please check your inputs and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputClass = "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 px-3 py-2 border";
  const labelClass = "block text-sm font-medium text-gray-700";

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 bg-gray-50 rounded-lg shadow-sm">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Submit New Event</h1>
        <p className="text-lg text-gray-600 max-w-2xl">Enter event details below.</p>
      </div>
      {error && <div className="text-red-600 mb-4">{error}</div>}
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label htmlFor="url" className={labelClass}>Event URL</label>
          <input
            id="url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className={inputClass}
            required
          />
        </div>
        <div>
          <label htmlFor="text" className={labelClass}>Pasted Text</label>
          <textarea
            id="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            className={`${inputClass} h-24 resize-none`}
            required
          />
        </div>
        <div>
          <label htmlFor="topic-hints" className={labelClass}>Topic Hints</label>
          <input
            id="topic-hints"
            type="text"
            value={topicHints}
            onChange={(e) => setTopicHints(e.target.value)}
            className={inputClass}
            placeholder="e.g. politics, technology, environment"
          />
        </div>
        <div>
          <label htmlFor="notes" className={labelClass}>Additional Notes</label>
          <textarea
            id="notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className={`${inputClass} h-24 resize-none`}
            placeholder="Any additional context or requirements"
          />
        </div>
        <div className="md:col-span-2">
          <button
            type="submit"
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Submitting..." : "Submit Event"}
          </button>
        </div>
      </form>
    </div>
  );
}
