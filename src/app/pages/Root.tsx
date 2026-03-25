import { Outlet, Link, useLocation } from 'react-router';
import { Activity, ClipboardList } from 'lucide-react';

export function Root() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-blue-950">
      {/* Navigation */}
      <nav className="bg-blue-950/50 backdrop-blur-sm border-b border-blue-700/50">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <Activity className="w-8 h-8 text-white" />
              <span className="text-xl font-bold text-white">Gimnasio Profesional</span>
            </div>
            <div className="flex gap-2">
              <Link
                to="/"
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  location.pathname === '/'
                    ? 'bg-white text-blue-900 font-semibold'
                    : 'text-white hover:bg-blue-800/50'
                }`}
              >
                <Activity className="w-5 h-5" />
                Control en Vivo
              </Link>
              <Link
                to="/registro"
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  location.pathname === '/registro'
                    ? 'bg-white text-blue-900 font-semibold'
                    : 'text-white hover:bg-blue-800/50'
                }`}
              >
                <ClipboardList className="w-5 h-5" />
                Registro Diario
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Page Content */}
      <Outlet />
    </div>
  );
}
