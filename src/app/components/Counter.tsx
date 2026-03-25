import { Activity, Pause, Play, TrendingUp, TrendingDown } from 'lucide-react';
import { useState, useEffect } from 'react';

interface CounterProps {
  count: number;
  maxCapacity: number;
  isSystemActive: boolean;
  onToggleSystem: () => void;
}

export function Counter({ count, maxCapacity, isSystemActive, onToggleSystem }: CounterProps) {
  const [previousCount, setPreviousCount] = useState(count);
  const [trend, setTrend] = useState<'up' | 'down' | 'stable'>('stable');

  useEffect(() => {
    if (count > previousCount) {
      setTrend('up');
    } else if (count < previousCount) {
      setTrend('down');
    } else {
      setTrend('stable');
    }
    setPreviousCount(count);
  }, [count, previousCount]);

  const percentage = (count / maxCapacity) * 100;
  const availableSpots = Math.max(0, maxCapacity - count);
  const exceeded = count > maxCapacity;

  return (
    <div className="flex flex-col items-center">
      <div className="flex items-center gap-2 mb-6">
        <Activity className="w-6 h-6 text-white" />
        <h2 className="text-2xl font-bold text-white">Lectura Automática</h2>
      </div>
      
      {/* Current Count Display */}
      <div className="mb-8">
        <div className="flex items-center justify-center gap-3 mb-2">
          <div className={`text-8xl font-bold ${exceeded ? 'text-red-300' : 'text-white'}`}>
            {count}
          </div>
          {trend === 'up' && (
            <TrendingUp className="w-8 h-8 text-green-300 animate-bounce" />
          )}
          {trend === 'down' && (
            <TrendingDown className="w-8 h-8 text-red-300 animate-bounce" />
          )}
        </div>
        <div className="text-center text-blue-100">
          <div className="text-xl">
            {exceeded ? (
              <>
                <span className="text-red-300 font-bold">SOBRE CAPACIDAD</span>
                <div className="text-sm mt-1">Capacidad recomendada: {maxCapacity} personas</div>
              </>
            ) : (
              <>de {maxCapacity} personas</>
            )}
          </div>
          {!exceeded && (
            <div className="text-lg mt-2">
              Lugares disponibles: <span className="font-semibold text-green-300">{availableSpots}</span>
            </div>
          )}
          {exceeded && (
            <div className="text-lg mt-2">
              Exceso: <span className="font-semibold text-red-300">+{count - maxCapacity}</span> personas
            </div>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full mb-8">
        <div className="h-4 bg-white/20 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              percentage < 65 ? 'bg-green-400' :
              percentage < 90 ? 'bg-yellow-400' :
              percentage <= 100 ? 'bg-red-400' :
              'bg-red-600'
            }`}
            style={{ width: `${Math.min(100, percentage)}%` }}
          />
        </div>
        <div className="text-center mt-2 text-sm text-blue-200">
          {percentage.toFixed(1)}% de capacidad
        </div>
      </div>

      {/* System Status */}
      <div className="bg-white/10 rounded-lg p-4 w-full mb-4 border border-white/20">
        <div className="text-sm text-blue-200 mb-2">Estado del Sistema</div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${isSystemActive ? 'bg-green-400 animate-pulse' : 'bg-gray-400'}`} />
            <span className="font-semibold text-white">
              {isSystemActive ? 'Detectando movimiento...' : 'Sistema pausado'}
            </span>
          </div>
          <button
            onClick={onToggleSystem}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              isSystemActive
                ? 'bg-yellow-500 hover:bg-yellow-600 text-white'
                : 'bg-green-500 hover:bg-green-600 text-white'
            }`}
          >
            {isSystemActive ? (
              <>
                <Pause className="w-4 h-4" />
                Pausar
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Activar
              </>
            )}
          </button>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-white/10 border border-white/30 rounded-lg p-4 w-full">
        <p className="text-sm text-blue-100">
          <strong className="text-white">Sistema de Visión Computarizada:</strong> El conteo se actualiza automáticamente 
          mediante análisis de video en tiempo real de las cámaras de entrada y salida.
        </p>
      </div>
    </div>
  );
}