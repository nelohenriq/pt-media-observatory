/** API client for PT Media Observatory backend. */
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface EventSubmission {
  url?: string;
  text?: string;
  topicHints?: string;
  notes?: string;
}

export interface Event {
  id: string;
  title: string;
  topic?: string;
  status: string;
  score?: number;
  date: string;
}

export interface Draft {
  id: string;
  title: string;
  content: string;
  status: string;
  createdAt: string;
}

export async function submitEvent(data: EventSubmission): Promise<void> {
  const res = await fetch(`${API_BASE}/submissions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Submission failed: ${res.status}`);
}

export async function fetchEvents(): Promise<Event[]> {
  const res = await fetch(`${API_BASE}/events/`);
  if (!res.ok) throw new Error(`Failed to fetch events: ${res.status}`);
  return res.json();
}

export async function fetchDrafts(): Promise<Draft[]> {
  // No /drafts endpoint yet — return empty array for now
  return [];
}
