import { useState, useCallback } from 'react';
import {
  Lock, LogOut, Plus, Minus, Download, ShieldCheck,
  Wifi, WifiOff, ArrowDownCircle, ArrowUpCircle, Calendar, TrendingUp,
} from 'lucide-react';
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

type LogEntry = { type: 'entrada' | 'salida'; timestamp: Date };

const todayKey = () => `gym_log_${new Date().toISOString().slice(0, 10)}`;

function loadLog(): { entries: LogEntry[]; totalEntries: number; totalExits: number } {
  try {
    const raw = localStorage.getItem(todayKey());
    if (!raw) return { entries: [], totalEntries: 0, totalExits: 0 };
    const data = JSON.parse(raw) as {
      entries: Array<{ type: string; timestamp: string }>;
      totalEntries: number;
      totalExits: number;
    };
    return {
      entries: data.entries.map(e => ({
        type: e.type as 'entrada' | 'salida',
        timestamp: new Date(e.timestamp),
      })),
      totalEntries: data.totalEntries,
      totalExits: data.totalExits,
    };
  } catch {
    return { entries: [], totalEntries: 0, totalExits: 0 };
  }
}

function saveLog(entries: LogEntry[], totalEntries: number, totalExits: number) {
  try {
    localStorage.setItem(todayKey(), JSON.stringify({
      entries: entries.map(e => ({ type: e.type, timestamp: e.timestamp.toISOString() })),
      totalEntries,
      totalExits,
    }));
  } catch { /* ignore quota errors */ }
}

// Module-level log state — survives AdminDashboard remounts within the session
let _log = loadLog();

function AdminDashboard({ onLogout }: { onLogout: () => void }) {
  const [downloading, setDownloading] = useState(false);
  const [entries, setEntries] = useState<LogEntry[]>(_log.entries);
  const [totalEntries, setTotalEntries] = useState(_log.totalEntries);
  const [totalExits, setTotalExits] = useState(_log.totalExits);

  const handleDelta = useCallback((delta: number) => {
    const now = new Date();
    const added = Array.from(
      { length: Math.abs(delta) },
      () => ({ type: (delta > 0 ? 'entrada' : 'salida') as 'entrada' | 'salida', timestamp: now }),
    );
    _log.entries = [..._log.entries, ...added];
    if (delta > 0) _log.totalEntries += delta;
    else _log.totalExits += Math.abs(delta);
    saveLog(_log.entries, _log.totalEntries, _log.totalExits);
    setEntries([..._log.entries]);
    setTotalEntries(_log.totalEntries);
    setTotalExits(_log.totalExits);
  }, []);

  const { count, connected, sendCommand } = useCounterWebSocket(handleDelta);
  const netFlow = totalEntries - totalExits;

  const handleDownload = () => {
    setDownloading(true);
    sendCommand('download_excel');
    setTimeout(() => setDownloading(false), 3000);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
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

      {/* Count + Manual adjustment side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="bg-white/8 backdrop-blur-md rounded-2xl border border-white/15 p-8 text-center">
          <p className="text-white/40 text-xs uppercase tracking-widest mb-2">Personas actualmente</p>
          <div className="text-8xl font-black text-white tabular-nums mb-2">{count}</div>
          <p className="text-white/30 text-sm">Conteo en tiempo real</p>
        </div>

        <div className="bg-white/8 backdrop-blur-md rounded-2xl border border-white/15 p-6 flex flex-col justify-between">
          <div>
            <h2 className="text-white font-semibold mb-1">Ajuste Manual</h2>
            <p className="text-white/40 text-xs mb-5">
              Corrige el contador si la cámara no detectó una entrada o salida.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => sendCommand('increment')}
              disabled={!connected}
              className="flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold py-5 rounded-2xl transition-all text-lg"
            >
              <Plus className="w-6 h-6" />
              +1
            </button>
            <button
              onClick={() => sendCommand('decrement')}
              disabled={!connected}
              className="flex items-center justify-center gap-2 bg-red-600 hover:bg-red-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold py-5 rounded-2xl transition-all text-lg"
            >
              <Minus className="w-6 h-6" />
              −1
            </button>
          </div>
        </div>
      </div>

      {/* Export */}
      <div className="bg-white/8 backdrop-blur-md rounded-2xl border border-white/15 p-6 mb-10">
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

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
        <div className="bg-gradient-to-br from-green-600/80 to-green-700/80 backdrop-blur-md rounded-2xl shadow-lg p-6 border border-green-400/20">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-green-200 text-xs font-medium uppercase tracking-wide">Entradas Totales</p>
              <h3 className="text-5xl font-black text-white mt-2 tabular-nums">{totalEntries}</h3>
            </div>
            <div className="bg-white/15 p-3 rounded-xl">
              <ArrowUpCircle className="w-7 h-7 text-white" />
            </div>
          </div>
          <p className="text-green-200/70 text-xs">Personas que ingresaron hoy</p>
        </div>

        <div className="bg-gradient-to-br from-red-600/80 to-red-700/80 backdrop-blur-md rounded-2xl shadow-lg p-6 border border-red-400/20">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-red-200 text-xs font-medium uppercase tracking-wide">Salidas Totales</p>
              <h3 className="text-5xl font-black text-white mt-2 tabular-nums">{totalExits}</h3>
            </div>
            <div className="bg-white/15 p-3 rounded-xl">
              <ArrowDownCircle className="w-7 h-7 text-white" />
            </div>
          </div>
          <p className="text-red-200/70 text-xs">Personas que salieron hoy</p>
        </div>

        <div className="bg-gradient-to-br from-[#0D6EBD]/80 to-[#003865]/80 backdrop-blur-md rounded-2xl shadow-lg p-6 border border-blue-400/20">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-blue-200 text-xs font-medium uppercase tracking-wide">Personas Adentro</p>
              <h3 className="text-5xl font-black text-white mt-2 tabular-nums">{netFlow}</h3>
            </div>
            <div className="bg-white/15 p-3 rounded-xl">
              <TrendingUp className="w-7 h-7 text-white" />
            </div>
          </div>
          <p className="text-blue-200/70 text-xs">Flujo neto actual</p>
        </div>
      </div>

      {/* Activity log */}
      <div className="bg-white/8 backdrop-blur-md rounded-2xl shadow-lg p-8 border border-white/15 mb-6">
        <h3 className="text-base font-bold text-white mb-5">Registro de Actividad</h3>
        {entries.length === 0 ? (
          <div className="text-center py-14">
            <Calendar className="w-14 h-14 text-white/20 mx-auto mb-4" />
            <p className="text-white/30 text-sm">No hay actividad registrada hoy</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
            {entries
              .slice()
              .reverse()
              .map((entry, index) => (
                <div
                  key={index}
                  className={`flex items-center justify-between px-4 py-3 rounded-xl ${
                    entry.type === 'entrada'
                      ? 'bg-green-500/15 border border-green-400/20'
                      : 'bg-red-500/15 border border-red-400/20'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {entry.type === 'entrada' ? (
                      <ArrowUpCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
                    ) : (
                      <ArrowDownCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                    )}
                    <div>
                      <p className="text-white text-sm font-semibold capitalize">{entry.type}</p>
                      <p className="text-white/40 text-xs">
                        {entry.timestamp.toLocaleTimeString('es-MX', {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })}
                      </p>
                    </div>
                  </div>
                  <span className="text-white/30 text-xs">Detección automática</span>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="bg-white/8 backdrop-blur-md rounded-2xl shadow-lg p-6 border border-white/15">
          <h3 className="text-base font-bold text-white mb-4">Estadísticas del Día</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-white/50 text-sm">Promedio por hora</span>
              <span className="text-white font-semibold text-sm">
                {totalEntries > 0
                  ? Math.round(totalEntries / (new Date().getHours() || 1))
                  : 0}{' '}
                entradas
              </span>
            </div>
            <div className="w-full h-px bg-white/10" />
            <div className="flex justify-between items-center">
              <span className="text-white/50 text-sm">Tasa de ocupación</span>
              <span className="text-white font-semibold text-sm">
                {totalEntries > 0 ? Math.round((netFlow / 40) * 100) : 0}%
              </span>
            </div>
            <div className="w-full h-px bg-white/10" />
            <div className="flex justify-between items-center">
              <span className="text-white/50 text-sm">Total de movimientos</span>
              <span className="text-white font-semibold text-sm">{totalEntries + totalExits}</span>
            </div>
          </div>
        </div>

        <div className="bg-white/8 backdrop-blur-md rounded-2xl shadow-lg p-6 border border-white/15">
          <h3 className="text-base font-bold text-white mb-4">Acerca del Sistema</h3>
          <p className="text-white/50 text-sm leading-relaxed mb-3">
            Los datos se registran automáticamente con el sistema de visión computarizada con IA instalado en la entrada del gimnasio.
          </p>
          <p className="text-white/30 text-xs leading-relaxed">
            Tecnología: Raspberry Pi · IMX500 · MobileNetV2 · Precisión estimada 98 %
          </p>
        </div>
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
