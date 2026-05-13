import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { fetchDraft } from '@/api/client';

export default function DraftPreview({ params }) {
  const router = useRouter();
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDraft(params.id)
      .then(res => setDraft(res.content))
      .catch(err => setError('Failed to load draft'));
  }, [params.id]);

  if (loading) return <p>Loading...</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="prose max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-2">Draft Preview</h1>
      <article className="mb-4">{draft}</article>
      <div className="flex gap-2 mt-4">
        <button className="rounded border bg-gray-200 px-3 py-1 text-sm">Copy</button>
        <a href="#" className="rounded bg-indigo-600 text-white px-3 py-1 text-sm">Export</a>
      </div>
    </div>
  );
}