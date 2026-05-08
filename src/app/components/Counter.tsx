import { Activity, TrendingUp, TrendingDown } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';

interface CounterProps {
  count: number;
  maxCapacity: number;
}

export function Counter({ count, maxCapacity }: CounterProps) {
  const previousCountRef = useRef(count);
  const [trend, setTrend] = useState<'up' | 'down' | 'stable'>('stable');

  useEffect(() => {
    if (count > previousCountRef.current) setTrend('up');
    else if (count < previousCountRef.current) setTrend('down');
    else setTrend('stable');
    previousCountRef.current = count;
  }, [count]);

  const percentage = (count / maxCapacity) * 100;
  const availableSpots = Math.max(0, maxCapacity - count);
  const exceeded = count > maxCapacity;

  return (
    <div className="flex flex-col items-center">
      <div className="flex items-center gap-2 mb-6">
        <Activity className="w-5 h-5 text-[#7EC8E3]" />
        <h2 className="text-xl font-bold text-white">Conteo en Tiempo Real</h2>
      </div>

      {/* Count */}
      <div className="mb-8">
        <div className="flex items-center justify-center gap-4 mb-3">
          <div className={`text-8xl font-black tabular-nums ${exceeded ? 'text-red-300' : 'text-white'}`}>
            {count}
          </div>
          {trend === 'up' && <TrendingUp className="w-8 h-8 text-green-400 animate-bounce" />}
          {trend === 'down' && <TrendingDown className="w-8 h-8 text-red-400 animate-bounce" />}
        </div>
        <div className="text-center">
          {exceeded ? (
            <>
              <span className="text-red-300 font-bold text-lg">SOBRE CAPACIDAD</span>
              <div className="text-sm text-white/50 mt-1">Máximo: {maxCapacity} personas</div>
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
      <div className="w-full mb-6">
        <div className="h-3 bg-white/15 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              percentage < 66.7 ? 'bg-green-400' :
              percentage < 100 ? 'bg-yellow-400' :
              percentage <= 100 ? 'bg-red-400' : 'bg-red-600'
            }`}
            style={{ width: `${Math.min(100, percentage)}%` }}
          />
        </div>
        <div className="text-center mt-2 text-xs text-white/50">
          {percentage.toFixed(1)}% de capacidad
        </div>
      </div>

      {/* Info */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4 w-full">
        <p className="text-xs text-white/40 leading-relaxed">
          <span className="text-white/60 font-medium">YOLO26n · IMX500</span> — Detección de personas en tiempo real mediante IA. El conteo se actualiza al cruzar la línea de acceso.
        </p>
      </div>
    </div>
  );
}
