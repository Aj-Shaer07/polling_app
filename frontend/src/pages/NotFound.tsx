import React from 'react';
import { Link } from 'react-router-dom';

export const NotFound: React.FC = () => {
  return (
    <div className="min-h-[70vh] flex items-center justify-center text-center px-4">
      <div className="space-y-4">
        <h1 className="text-6xl font-extrabold text-indigo-600">404</h1>
        <h2 className="text-xl font-bold text-slate-900">Page Not Found</h2>
        <p className="text-sm text-slate-500 max-w-sm mx-auto">
          The requested page could not be found or you may not have authorization to view it.
        </p>
        <Link
          to="/"
          className="inline-block px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-colors"
        >
          Return Home
        </Link>
      </div>
    </div>
  );
};
