import { useState, useEffect, useCallback } from 'react';
import { TrafficLight } from '../components/TrafficLight';
import { CameraFeed } from '../components/CameraFeed';
import { Counter } from '../components/Counter';
import { Users, AlertTriangle } from 'lucide-react';
import { useGymData } from '../hooks/useGymData';
import { useCounterWebSocket } from '../hooks/useCounterWebSocket';

const MAX_CAPACITY = 40;

export function Dashboard() {
  const [currentCount, setCurrentCount] = useState(0);
  const [showAlert, setShowAlert] = useState(false);
  const [isSystemActive, setIsSystemActive] = useState(true);
  const { addEntry, addExit } = useGymData();

  // Called by the WebSocket hook whenever the backend count changes.
  const handleDelta = useCallback(
    (delta: number) => {
      if (delta > 0) {
        for (let i = 0; i < delta; i++) addEntry();
      } else {
        for (let i = 0; i < Math.abs(delta); i++) addExit();
      }
    },
    [addEntry, addExit],
  );

  const { count: wsCount, connected: wsConnected } = useCounterWebSocket(handleDelta);

  // When WebSocket delivers a real count, apply it directly.
  useEffect(() => {
    if (wsConnected) {
      setCurrentCount(wsCount);
    }
  }, [wsCount, wsConnected]);

  // Simulation fallback – only active when the Pi is not reachable.
  useEffect(() => {
    if (wsConnected || !isSystemActive) return;

    const interval = setInterval(() => {
      const change = Math.floor(Math.random() * 3) - 1; // -1, 0, or +1
      setCurrentCount((prev) => {
        const newCount = Math.max(0, Math.min(60, prev + change));
        if (change === 1) addEntry();
        else if (change === -1 && prev > 0) addExit();
        return newCount;
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [wsConnected, isSystemActive, addEntry, addExit]);

  // Capacity alert
  useEffect(() => {
    setShowAlert(currentCount > MAX_CAPACITY);
  }, [currentCount]);

  const getCapacityPercentage = () => (currentCount / MAX_CAPACITY) * 100;
  const handleToggleSystem = () => setIsSystemActive((s) => !s);

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-2">
          <Users className="w-10 h-10 text-white" />
          <h1 className="text-4xl font-bold text-white">Contador de personas</h1>
        </div>
        <p className="text-blue-200">Capacidad máxima recomendada: {MAX_CAPACITY} personas</p>
        <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
          <div className="flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${isSystemActive ? 'bg-green-400 animate-pulse' : 'bg-gray-400'}`}
            />
            <span className="text-sm text-blue-200">
              Sistema de visión computarizada: {isSystemActive ? 'ACTIVO' : 'PAUSADO'}
            </span>
          </div>
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              wsConnected
                ? 'bg-green-500/30 text-green-300'
                : 'bg-yellow-500/30 text-yellow-300'
            }`}
          >
            {wsConnected ? '● Raspberry Pi conectada' : '○ Simulación (sin conexión)'}
          </span>
        </div>
      </div>

      {/* Alert Banner */}
      {showAlert && (
        <div className="mb-6 bg-red-500 border-2 border-red-300 rounded-xl p-4 animate-pulse">
          <div className="flex items-center gap-3 text-white">
            <AlertTriangle className="w-8 h-8" />
            <div>
              <div className="font-bold text-xl">¡ALERTA DE CAPACIDAD EXCEDIDA!</div>
              <div className="text-sm">
                Se ha superado el límite de {MAX_CAPACITY} personas. Exceso:{' '}
                {currentCount - MAX_CAPACITY} personas
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Control Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white/10 backdrop-blur-md rounded-xl shadow-lg p-8 border border-white/20">
          <Counter
            count={currentCount}
            maxCapacity={MAX_CAPACITY}
            isSystemActive={isSystemActive}
            onToggleSystem={handleToggleSystem}
          />
        </div>
        <div className="bg-white/10 backdrop-blur-md rounded-xl shadow-lg p-8 border border-white/20">
          <TrafficLight
            percentage={getCapacityPercentage()}
            currentCount={currentCount}
            maxCapacity={MAX_CAPACITY}
          />
        </div>
      </div>

      {/* Camera Feeds Section */}
      <div className="bg-white/10 backdrop-blur-md rounded-xl shadow-lg p-8 border border-white/20">
        <h2 className="text-2xl font-bold text-white mb-6">Cámaras de Seguridad</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <CameraFeed title="Cámara - Entrada" cameraId="entrada" />
          <CameraFeed title="Cámara - Salida" cameraId="salida" />
        </div>
      </div>
    </div>
  );
}
