import { useState, useCallback } from 'react';
import { Lock, LogOut, Plus, Minus, Download, ShieldCheck, Wifi, WifiOff } from 'lucide-react';
import { useCounterWebSocket } from '../hooks/useCounterWebSocket';

const ADMIN_USER = (import.meta.env.VITE_ADMIN_USER as string | undefined) ?? 'admin';
const ADMIN_PASS = (import.meta.env.VITE_ADMIN_PASSWORD as string | undefined) ?? 'admin';

function LoginForm({ onLogin }: { onLogin: () => void }) {
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (user === ADMIN_USER && pass === ADMIN_PASS) {
      sessionStorage.setItem('admin_auth', 'true');
      onLogin();
    } else {
      setError('Usuario o contraseña incorrectos');
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white/10 border border-white/20 mb-4">
            <Lock className="w-7 h-7 text-[#7EC8E3]" />
          </div>
          <h1 className="text-2xl font-bold text-white">Panel de Administración</h1>
          <p className="text-white/40 text-sm mt-1">Gym · Tec de Monterrey Campus EdoMex</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white/8 backdrop-blur-md rounded-2xl p-6 border border-white/15 space-y-4">
          <div>
            <label className="block text-xs text-white/50 uppercase tracking-wide mb-1.5">
              Usuario
            </label>
            <input
              type="text"
              value={user}
              onChange={(e) => setUser(e.target.value)}
              className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-2.5 text-white placeholder-white/30 focus:outline-none focus:border-[#7EC8E3]/60 text-sm"
              placeholder="Ingresa tu usuario"
              autoComplete="username"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 uppercase tracking-wide mb-1.5">
              Contraseña
            </label>
            <input
              type="password"
              value={pass}
              onChange={(e) => setPass(e.target.value)}
              className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-2.5 text-white placeholder-white/30 focus:outline-none focus:border-[#7EC8E3]/60 text-sm"
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>
          {error && (
            <p className="text-red-400 text-xs text-center">{error}</p>
          )}
          <button
            type="submit"
            className="w-full bg-[#0D6EBD] hover:bg-[#0a5a9e] text-white font-semibold py-2.5 rounded-xl transition-all text-sm"
          >
            Iniciar sesión
          </button>
        </form>
      </div>
    </div>
  );
}

function AdminDashboard({ onLogout }: { onLogout: () => void }) {
  const [downloading, setDownloading] = useState(false);

  const { count, connected, sendCommand } = useCounterWebSocket(useCallback(() => {}, []));

  const handleDownload = () => {
    setDownloading(true);
    sendCommand('download_excel');
    setTimeout(() => setDownloading(false), 3000);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheck className="w-5 h-5 text-[#7EC8E3]" />
            <h1 className="text-xl font-bold text-white">Panel de Administración</h1>
          </div>
          <p className="text-white/40 text-xs">Gym · Tec de Monterrey Campus EdoMex</p>
        </div>
        <button
          onClick={onLogout}
          className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/8 border border-white/15 text-white/60 hover:text-white hover:bg-white/15 transition-all text-sm"
        >
          <LogOut className="w-4 h-4" />
          Salir
        </button>
      </div>

      {/* Connection status */}
      <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border mb-6 text-sm ${
        connected
          ? 'bg-green-500/15 border-green-400/30 text-green-300'
          : 'bg-amber-500/15 border-amber-400/30 text-amber-300'
      }`}>
        {connected
          ? <><Wifi className="w-4 h-4" /> Raspberry Pi conectada</>
          : <><WifiOff className="w-4 h-4" /> Sin conexión con la Pi — los comandos no tendrán efecto</>
        }
      </div>

      {/* Current count */}
      <div className="bg-white/8 backdrop-blur-md rounded-2xl border border-white/15 p-8 text-center mb-6">
        <p className="text-white/40 text-xs uppercase tracking-widest mb-2">Personas actualmente</p>
        <div className="text-8xl font-black text-white tabular-nums mb-2">{count}</div>
        <p className="text-white/30 text-sm">Conteo en tiempo real</p>
      </div>

      {/* Manual adjustment */}
      <div className="bg-white/8 backdrop-blur-md rounded-2xl border border-white/15 p-6 mb-6">
        <h2 className="text-white font-semibold mb-1">Ajuste Manual</h2>
        <p className="text-white/40 text-xs mb-5">
          Usa estos botones para corregir el contador si la cámara no detectó una entrada o salida.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => sendCommand('increment')}
            disabled={!connected}
            className="flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold py-5 rounded-2xl transition-all text-lg"
          >
            <Plus className="w-6 h-6" />
            Entrada (+1)
          </button>
          <button
            onClick={() => sendCommand('decrement')}
            disabled={!connected}
            className="flex items-center justify-center gap-2 bg-red-600 hover:bg-red-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold py-5 rounded-2xl transition-all text-lg"
          >
            <Minus className="w-6 h-6" />
            Salida (−1)
          </button>
        </div>
      </div>

      {/* Download */}
      <div className="bg-white/8 backdrop-blur-md rounded-2xl border border-white/15 p-6">
        <h2 className="text-white font-semibold mb-1">Exportar Datos</h2>
        <p className="text-white/40 text-xs mb-5">
          Descarga el historial horario con predicciones de peak / off-peak en formato Excel.
        </p>
        <button
          onClick={handleDownload}
          disabled={!connected || downloading}
          className="flex items-center justify-center gap-2 w-full bg-[#0D6EBD] hover:bg-[#0a5a9e] disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-all text-sm"
        >
          <Download className="w-4 h-4" />
          {downloading ? 'Generando archivo...' : 'Descargar Excel'}
        </button>
      </div>
    </div>
  );
}

export function AdminPanel() {
  const [authenticated, setAuthenticated] = useState(
    () => sessionStorage.getItem('admin_auth') === 'true',
  );

  const handleLogout = () => {
    sessionStorage.removeItem('admin_auth');
    setAuthenticated(false);
  };

  if (!authenticated) {
    return <LoginForm onLogin={() => setAuthenticated(true)} />;
  }

  return <AdminDashboard onLogout={handleLogout} />;
}
