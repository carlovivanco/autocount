import { Outlet, Link, useLocation } from 'react-router';
import { Activity, ClipboardList } from 'lucide-react';

export function Root() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#001F3F] via-[#003865] to-[#001228]">
      {/* Top accent stripe */}
      <div className="h-1 bg-gradient-to-r from-[#0D6EBD] via-white to-[#0D6EBD]" />

      {/* Navigation */}
      <nav className="bg-[#002A52]/80 backdrop-blur-sm border-b border-white/10 shadow-lg">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Brand */}
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center bg-white text-[#003865] font-black text-base px-2.5 py-1.5 rounded-md tracking-tight leading-none select-none">
                TEC
              </div>
              <div className="flex flex-col leading-tight">
                <span className="text-white font-bold text-sm">Gimnasio</span>
                <span className="text-[#7EC8E3] text-xs">Campus Estado de México</span>
              </div>
            </div>

            {/* Nav links */}
            <div className="flex gap-2">
              <Link
                to="/"
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  location.pathname === '/'
                    ? 'bg-white text-[#003865] shadow-md'
                    : 'text-white/80 hover:text-white hover:bg-white/10'
                }`}
              >
                <Activity className="w-4 h-4" />
                Control en Vivo
              </Link>
              <Link
                to="/registro"
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  location.pathname === '/registro'
                    ? 'bg-white text-[#003865] shadow-md'
                    : 'text-white/80 hover:text-white hover:bg-white/10'
                }`}
              >
                <ClipboardList className="w-4 h-4" />
                Registro Diario
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Page Content */}
      <Outlet />

      {/* Footer */}
      <footer className="border-t border-white/10 mt-12 py-4">
        <div className="container mx-auto px-4 text-center">
          <p className="text-white/30 text-xs">
            Tecnológico de Monterrey · Campus Estado de México · Sistema de Monitoreo de Aforo
          </p>
        </div>
      </footer>
    </div>
  );
}
