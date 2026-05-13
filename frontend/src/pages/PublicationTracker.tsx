import { useState } from 'react';
import { Button, Card, CardHeader, CardBody, CardTitle, Table, TableHead, TableRow, Tablehead, TableCell, TableBody, Chip, Input } from '@/components/ui';

type Publication = {
  id: string;
  platform: string;
  date: string;
  status: 'published' | 'scheduled' | 'rejected' | 'pending';
  url: string;
  outlets?: string[];
};

export default function PublicationTracker() {
  const [searchQuery, setSearchQuery] = useState('');
  const [publications, setPublications] = useState<Publication[]>([
    {
      id: 'pub-001',
      platform: 'The Guardian',
      date: '2026-05-10',
      status: 'published',
      url: 'https://theguardian.com/article/1',
      outlets: ['theguardian'],
    },
    {
      id: 'pub-002',
      platform: 'TechCrunch',
      date: '2026-05-12',
      status: 'scheduled',
      url: 'https://techcrunch.com/article/2',
      outlets: ['techcrunch'],
    },
    {
      id: 'pub-003',
      platform: 'Le Monde',
      date: '2026-05-13',
      status: 'pending',
      url: 'https://lemonde.fr/article/3',
      outlets: ['lemonde'],
    },
    {
      id: 'pub-004',
      platform: 'Financial Times',
      date: '2026-05-08',
      status: 'rejected',
      url: 'https://ft.com/article/4',
      outlets: ['ft'],
    },
  ]);

  const filteredPublications = publications.filter(p =>
    p.platform.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handlePublish = (id: string) => {
    // TODO: API call to publish
    console.log(`Published ${id}`);
  };

  const handleRemove = (id: string) => {
    // TODO: API call to retract
    console.log(`Removed ${id}`);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 bg-gray-50 rounded-lg shadow-sm">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Publication Tracker</h1>
        <p className="text-lg text-gray-600 max-w-2xl">
          Monitor where and when your drafts are published across outlets.
        </p>
      </div>

      <div className="flex gap-2 mb-4">
        <Input
          type="text"
          placeholder="Filter by platform..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 px-3 py-2"
        />
        <Button variant="outline" className="rounded-md border-gray-300 shadow-sm px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
          Add New
        </Button>
      </div>

      <Card>
        <CardHeader>Publications</CardHeader>
        <CardBody>
          <Table className="w-full text-sm">
            <TableHead>
              <TableRow>
                <Tablehead>
                  <TableCell>Outlets</TableCell>
                </Tablehead>
                <Tablehead>
                  <TableCell>Date</TableCell>
                </Tablehead>
                <Tablehead>
                  <TableCell>Status</TableCell>
                </Tablehead>
                <Tablehead>
                  <TableCell>Platform</TableCell>
                </Tablehead>
                <Tablehead>
                  <TableCell>URL</TableCell>
                </Tablehead>
                <Tablehead>
                  <TableCell>Actions</TableCell>
                </Tablehead>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredPublications.length > 0 ? (
                filteredPublications.map((pub) => (
                  <TableRow key={pub.id} className="border-b">
                    <TableCell>
                      {pub.outlets?.map((outlet) => (
                        <Chip key={outlet} className="self-inherit BG-INDIAN_RUBY_DARK text-white text-xs px-2.5 py-0.5 rounded-full">
                          {outlet}
                        </Chip>
                      ))}
                    </TableCell>
                    <TableCell>{pub.date}</TableCell>
                    <TableCell>
                      <Chip
                        className={`self-inherit ${
                          pub.status === 'published'
                            ? 'bg-green-600'
                            : pub.status === 'scheduled'
                            ? 'bg-yellow-600'
                            : pub.status === 'rejected'
                            ? 'bg-red-600'
                            : 'bg-gray-400'
                        } text-white text-xs px-2.5 py-0.5 rounded-full`}
                      >
                        {pub.status}
                      </Chip>
                    </TableCell>
                    <TableCell>{pub.platform}</TableCell>
                    <TableCell><a href={pub.url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 underline">{pub.url}</a></TableCell>
                    <TableCell className="flex gap-1">
                      <Button onClick={() => handlePublish(pub.id)} className="rounded border bg-gray-200 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50">
                        Track
                      </Button>
                      <Button variant="danger" onClick={() => handleRemove(pub.id)} className="rounded border bg-gray-200 px-2 py-1 text-xs font-medium text-red-600 hover:bg-gray-50">
                        Retract
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-3 text-gray-500">
                    No publications match your filter.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardBody>
      </Card>
    </div>
  );
}