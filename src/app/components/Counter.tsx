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
        <Activity className="w-5 h-5 text-[#7EC8E3]" />
        <h2 className="text-xl font-bold text-white">Conteo en Tiempo Real</h2>
      </div>

      {/* Current Count Display */}
      <div className="mb-8">
        <div className="flex items-center justify-center gap-4 mb-3">
          <div className={`text-8xl font-black tabular-nums ${exceeded ? 'text-red-300' : 'text-white'}`}>
            {count}
          </div>
          {trend === 'up' && (
            <TrendingUp className="w-8 h-8 text-green-400 animate-bounce" />
          )}
          {trend === 'down' && (
            <TrendingDown className="w-8 h-8 text-red-400 animate-bounce" />
          )}
        </div>
        <div className="text-center">
          {exceeded ? (
            <>
              <span className="text-red-300 font-bold text-lg">SOBRE CAPACIDAD</span>
              <div className="text-sm text-white/50 mt-1">Máximo recomendado: {maxCapacity} personas</div>
            </>
          ) : (
            <span className="text-white/60 text-lg">de {maxCapacity} personas</span>
          )}
          <div className="mt-2 text-base">
            {!exceeded ? (
              <>Lugares disponibles: <span className="font-bold text-green-400">{availableSpots}</span></>
            ) : (
              <>Exceso: <span className="font-bold text-red-300">+{count - maxCapacity}</span> personas</>
            )}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full mb-8">
        <div className="h-3 bg-white/15 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              percentage < 65 ? 'bg-green-400' :
              percentage < 90 ? 'bg-yellow-400' :
              percentage <= 100 ? 'bg-red-400' :
              'bg-red-600'
            }`}
            style={{ width: `${Math.min(100, percentage)}%` }}
          />
        </div>
        <div className="text-center mt-2 text-xs text-white/50">
          {percentage.toFixed(1)}% de capacidad
        </div>
      </div>

      {/* System Status */}
      <div className="bg-white/8 rounded-xl p-4 w-full mb-4 border border-white/15">
        <div className="text-xs text-white/40 mb-2 uppercase tracking-wide">Estado del Sistema</div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full ${isSystemActive ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
            <span className="text-sm font-medium text-white">
              {isSystemActive ? 'Detectando movimiento...' : 'Sistema pausado'}
            </span>
          </div>
          <button
            onClick={onToggleSystem}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isSystemActive
                ? 'bg-amber-500 hover:bg-amber-600 text-white'
                : 'bg-green-500 hover:bg-green-600 text-white'
            }`}
          >
            {isSystemActive ? (
              <><Pause className="w-3.5 h-3.5" /> Pausar</>
            ) : (
              <><Play className="w-3.5 h-3.5" /> Activar</>
            )}
          </button>
        </div>
      </div>

      {/* Info */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4 w-full">
        <p className="text-xs text-white/40 leading-relaxed">
          <span className="text-white/60 font-medium">IMX500 · MobileNetV2</span> — Detección de personas mediante IA embebida en la cámara. El conteo se actualiza automáticamente al cruzar la línea de acceso.
        </p>
      </div>
    </div>
  );
}
