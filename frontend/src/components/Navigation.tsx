import { Link } from "react-router-dom";

const Navigation = () => {
  return (
    <nav className="flex gap-4 mb-4 p-3 bg-white rounded-lg shadow-sm">
      <Link to="/submission" className="text-sm font-medium text-blue-600 hover:underline">
        Submission
      </Link>
      <Link to="/events" className="text-sm font-medium text-blue-600 hover:underline">
        Events
      </Link>
      <Link to="/drafts" className="text-sm font-medium text-blue-600 hover:underline">
        Drafts
      </Link>
      <Link to="/review" className="text-sm font-medium text-blue-600 hover:underline">
        Review
      </Link>
    </nav>
  );
};

export default Navigation;
