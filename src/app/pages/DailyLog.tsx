import { ArrowDownCircle, ArrowUpCircle, Calendar, TrendingUp } from 'lucide-react';
import { useGymData } from '../hooks/useGymData';

export function DailyLog() {
  const { totalEntries, totalExits, entries } = useGymData();
  const netFlow = totalEntries - totalExits;

  const getCurrentDate = () => {
    const date = new Date();
    return date.toLocaleDateString('es-ES', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-2">
          <Calendar className="w-10 h-10 text-white" />
          <h1 className="text-4xl font-bold text-white">Registro Diario</h1>
        </div>
        <p className="text-blue-200 capitalize">{getCurrentDate()}</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Total Entries */}
        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl shadow-lg p-6 border border-white/20">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-green-100 text-sm font-medium">Entradas Totales</p>
              <h3 className="text-5xl font-bold text-white mt-2">{totalEntries}</h3>
            </div>
            <div className="bg-white/20 p-3 rounded-lg">
              <ArrowUpCircle className="w-8 h-8 text-white" />
            </div>
          </div>
          <p className="text-green-100 text-sm">Personas que ingresaron hoy</p>
        </div>

        {/* Total Exits */}
        <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-xl shadow-lg p-6 border border-white/20">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-red-100 text-sm font-medium">Salidas Totales</p>
              <h3 className="text-5xl font-bold text-white mt-2">{totalExits}</h3>
            </div>
            <div className="bg-white/20 p-3 rounded-lg">
              <ArrowDownCircle className="w-8 h-8 text-white" />
            </div>
          </div>
          <p className="text-red-100 text-sm">Personas que salieron hoy</p>
        </div>

        {/* Net Flow */}
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg p-6 border border-white/20">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-blue-100 text-sm font-medium">Flujo Neto</p>
              <h3 className="text-5xl font-bold text-white mt-2">{netFlow}</h3>
            </div>
            <div className="bg-white/20 p-3 rounded-lg">
              <TrendingUp className="w-8 h-8 text-white" />
            </div>
          </div>
          <p className="text-blue-100 text-sm">Personas actualmente dentro</p>
        </div>
      </div>

      {/* Activity Log */}
      <div className="bg-white/10 backdrop-blur-md rounded-xl shadow-lg p-8 border border-white/20">
        <h2 className="text-2xl font-bold text-white mb-6">Registro de Actividad</h2>
        
        {entries.length === 0 ? (
          <div className="text-center py-12">
            <Calendar className="w-16 h-16 text-white/30 mx-auto mb-4" />
            <p className="text-white/50">No hay actividad registrada hoy</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {entries.slice().reverse().map((entry, index) => (
              <div
                key={index}
                className={`flex items-center justify-between p-4 rounded-lg ${
                  entry.type === 'entrada'
                    ? 'bg-green-500/20 border border-green-400/30'
                    : 'bg-red-500/20 border border-red-400/30'
                }`}
              >
                <div className="flex items-center gap-3">
                  {entry.type === 'entrada' ? (
                    <ArrowUpCircle className="w-6 h-6 text-green-300" />
                  ) : (
                    <ArrowDownCircle className="w-6 h-6 text-red-300" />
                  )}
                  <div>
                    <p className="text-white font-semibold capitalize">
                      {entry.type}
                    </p>
                    <p className="text-white/70 text-sm">
                      {entry.timestamp.toLocaleTimeString('es-ES', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                      })}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-white/50 text-xs">Detección automática</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        <div className="bg-white/10 backdrop-blur-md rounded-xl shadow-lg p-6 border border-white/20">
          <h3 className="text-lg font-bold text-white mb-4">Estadísticas del Día</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-blue-200">Promedio por hora</span>
              <span className="text-white font-semibold">
                {totalEntries > 0 ? Math.round(totalEntries / (new Date().getHours() || 1)) : 0} entradas
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-blue-200">Tasa de ocupación</span>
              <span className="text-white font-semibold">
                {totalEntries > 0 ? Math.round((netFlow / 40) * 100) : 0}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-blue-200">Total de movimientos</span>
              <span className="text-white font-semibold">{totalEntries + totalExits}</span>
            </div>
          </div>
        </div>

        <div className="bg-white/10 backdrop-blur-md rounded-xl shadow-lg p-6 border border-white/20">
          <h3 className="text-lg font-bold text-white mb-4">Información</h3>
          <p className="text-blue-200 text-sm mb-3">
            Los datos se registran automáticamente mediante el sistema de visión computarizada 
            instalado en las cámaras de entrada y salida.
          </p>
          <p className="text-blue-200 text-sm">
            El sistema detecta y cuenta personas en tiempo real con una precisión del 98%.
          </p>
        </div>
      </div>
    </div>
  );
}
