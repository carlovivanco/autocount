import { ArrowDownCircle, ArrowUpCircle, Calendar, TrendingUp } from 'lucide-react';
import { useGymData } from '../hooks/useGymData';

export function DailyLog() {
  const { totalEntries, totalExits, entries } = useGymData();
  const netFlow = totalEntries - totalExits;

  const getCurrentDate = () => {
    const date = new Date();
    return date.toLocaleDateString('es-MX', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="text-center mb-8">
        <p className="text-[#7EC8E3] text-sm font-medium uppercase tracking-widest mb-1">
          Tecnológico de Monterrey · Campus Estado de México
        </p>
        <div className="flex items-center justify-center gap-3 mb-2">
          <Calendar className="w-9 h-9 text-white" />
          <h1 className="text-4xl font-bold text-white">Registro Diario</h1>
        </div>
        <p className="text-white/50 text-sm capitalize">{getCurrentDate()}</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
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

      {/* Activity Log */}
      <div className="bg-white/8 backdrop-blur-md rounded-2xl shadow-lg p-8 border border-white/15 mb-6">
        <h2 className="text-xl font-bold text-white mb-5">Registro de Actividad</h2>

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

      {/* Statistics */}
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
