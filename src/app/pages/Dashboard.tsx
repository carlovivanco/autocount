import { useState, useEffect, useCallback } from 'react';
import { TrafficLight } from '../components/TrafficLight';
import { Counter } from '../components/Counter';
import { PeakScheduleCard } from '../components/PeakSchedule';
import { Users, AlertTriangle, Clock, MapPin } from 'lucide-react';
import { useCounterWebSocket } from '../hooks/useCounterWebSocket';

const MAX_CAPACITY = 60;

export function Dashboard() {
  const [currentCount, setCurrentCount] = useState(0);
  const [showAlert, setShowAlert] = useState(false);

  const { count: wsCount, connected: wsConnected, peakPrediction, peakSchedule } = useCounterWebSocket(useCallback(() => {}, []));

  useEffect(() => {
    if (wsConnected) setCurrentCount(wsCount);
  }, [wsCount, wsConnected]);

  useEffect(() => {
    setShowAlert(currentCount > MAX_CAPACITY);
  }, [currentCount]);

  const getCapacityPercentage = () => (currentCount / MAX_CAPACITY) * 100;

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="text-center mb-8">
        <p className="text-[#7EC8E3] text-sm font-medium uppercase tracking-widest mb-1">
          Tecnológico de Monterrey · Campus Estado de México
        </p>
        <div className="flex items-center justify-center gap-3 mb-3">
          <Users className="w-9 h-9 text-white" />
          <h1 className="text-4xl font-bold text-white">Aforo del Gimnasio</h1>
        </div>
        <p className="text-white/50 text-sm">
          Capacidad máxima recomendada:{' '}
          <span className="text-white font-semibold">{MAX_CAPACITY} personas</span>
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3 mt-3">
          <span
            className={`text-xs px-3 py-1 rounded-full border ${
              wsConnected
                ? 'bg-green-500/20 border-green-400/40 text-green-300'
                : 'bg-amber-500/20 border-amber-400/40 text-amber-300'
            }`}
          >
            {wsConnected ? '● Raspberry Pi conectada' : '○ Sin conexión'}
          </span>
          {peakPrediction && (
            <span
              className={`text-xs px-3 py-1 rounded-full border font-medium ${
                peakPrediction === 'Peak'
                  ? 'bg-red-500/20 border-red-400/40 text-red-300'
                  : 'bg-sky-500/20 border-sky-400/40 text-sky-300'
              }`}
            >
              {peakPrediction === 'Peak' ? '▲ Hora Peak' : '▽ Hora Off-peak'}
            </span>
          )}
        </div>
      </div>

      {/* Alert */}
      {showAlert && (
        <div className="mb-6 bg-red-600/90 backdrop-blur-sm border border-red-400/60 rounded-xl p-4 animate-pulse shadow-lg shadow-red-900/50">
          <div className="flex items-center gap-3 text-white">
            <AlertTriangle className="w-7 h-7 flex-shrink-0" />
            <div>
              <div className="font-bold text-lg">¡ALERTA: CAPACIDAD EXCEDIDA!</div>
              <div className="text-sm text-red-100">
                Límite de {MAX_CAPACITY} personas superado · Exceso:{' '}
                {currentCount - MAX_CAPACITY} persona
                {currentCount - MAX_CAPACITY !== 1 ? 's' : ''}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-white/8 backdrop-blur-md rounded-2xl shadow-xl p-8 border border-white/15">
          <Counter count={currentCount} maxCapacity={MAX_CAPACITY} />
        </div>
        <div className="bg-white/8 backdrop-blur-md rounded-2xl shadow-xl p-8 border border-white/15">
          <TrafficLight
            percentage={getCapacityPercentage()}
            currentCount={currentCount}
            maxCapacity={MAX_CAPACITY}
          />
        </div>
      </div>

      {/* Peak Schedule */}
      {peakSchedule && (
        <div className="bg-white/8 backdrop-blur-md rounded-2xl p-6 border border-white/15 mb-6">
          <PeakScheduleCard schedule={peakSchedule} />
        </div>
      )}

      {/* Info Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white/8 backdrop-blur-md rounded-2xl p-6 border border-white/15">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-[#7EC8E3]" />
            <h3 className="text-white font-semibold">Horarios de Operación</h3>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-white/60">Lunes – Viernes</span>
              <span className="text-white font-medium">6:00 – 21:00</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/60">Sábado</span>
              <span className="text-white font-medium">8:00 – 12:00</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/60">Domingo</span>
              <span className="text-white font-medium">Cerrado</span>
            </div>
          </div>
        </div>
        <div className="bg-white/8 backdrop-blur-md rounded-2xl p-6 border border-white/15">
          <div className="flex items-center gap-2 mb-4">
            <MapPin className="w-5 h-5 text-[#7EC8E3]" />
            <h3 className="text-white font-semibold">Información</h3>
          </div>
          <p className="text-white/60 text-sm leading-relaxed">
            El conteo se actualiza en tiempo real mediante visión computarizada con IA instalada en la entrada del gimnasio.
          </p>
          <p className="text-white/40 text-xs mt-3">
            ¿Dudas? Contacta a Servicios Deportivos · Ext. 4200
          </p>
        </div>
      </div>
    </div>
  );
}
