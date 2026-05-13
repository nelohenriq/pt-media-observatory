import { useState, useEffect } from 'react';
import { fetchEvents } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table } from '@/components/ui/table';
import { TableHeader, TableRow, TableHead, TableBody, TableCaption, Checkbox, TableCell, TablePagination } from '@/components/ui/table';

export default function EventList() {
  const [events, setEvents] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);

  useEffect(() => {
    fetchEvents().then(setEvents);
  }, []);

  const filteredEvents = events.filter(event =>
    event.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (event.topic && event.topic.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const goPrev = () => {
    if (currentPage > 1) {
      setCurrentPage(prev => prev - 1);
    }
  };

  const goNext = () => {
    const maxPage = Math.ceil(filteredEvents.length / itemsPerPage);
    if (currentPage < maxPage) {
      setCurrentPage(prev => prev + 1);
    }
  };

  const goHome = () => {
    setCurrentPage(1);
  };

  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const pagedEvents = filteredEvents.slice(startIndex, endIndex);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 bg-gray-50 rounded-lg shadow-sm">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Events</h1>
      </div>
      
      <div className="mb-4 flex gap-2">
        <Input
          type="text"
          placeholder="Search events..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setCurrentPage(1); // Reset to first page on new search
          }}
          className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 px-3 py-2"
        />
        <Button
          variant="outline"
          onClick={() => window.location.reload()}
          className="rounded-md border-gray-300 shadow-sm px-3 py-2 text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
        >
          Refresh
        </Button>
      </div>
      
      {events.length === 0 && searchQuery === '' && (
        <div className="text-center py-10 text-gray-500">
          No events found. Try searching or check later.
        </div>
      )}
      
      {events.length > 0 && (
        <>
          <Table className="w-full text-sm">
            <TableCaption>Events</TableCaption>
            <TableHead>
              <TableRow>
                <Checkbox />
                <TableHead>Select</TableHead>
                <TableHead>Event</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHead>
            <TableBody>
              {pagedEvents.map((event, index) => (
                <TableRow key={index}>
                  <Checkbox />
                  <Checkbox />
                  <TableCell>{event.title}</TableCell>
                  <TableCell>{event.status}</TableCell>
                  <TableCell>{event.score}</TableCell>
                  <TableCell>{event.date}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          
          <div className="flex justify-between mt-4">
            <Button
              variant="secondary"
              onClick={goPrev}
              disabled={currentPage === 1}
              className="px-2 py-1 rounded text-sm text-gray-600 hover:text-gray-900"
            >
              Previous
            </Button>
            <span className="text-sm text-gray-500">
              Page {currentPage} of {Math.ceil(filteredEvents.length / itemsPerPage)}
            </span>
            <Button
              variant="secondary"
              onClick={goNext}
              disabled={currentPage >= Math.ceil(filteredEvents.length / itemsPerPage)}
              className="px-2 py-1 rounded text-sm text-gray-600 hover:text-gray-900"
            >
              Next
            </Button>
          </div>
          
          <TablePagination
            label={"Jump to page"} />
        </>
      )}
    </div>
  );
}