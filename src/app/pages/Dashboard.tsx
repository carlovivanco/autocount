import { useState, useEffect } from 'react';
import { TrafficLight } from '../components/TrafficLight';
import { CameraFeed } from '../components/CameraFeed';
import { Counter } from '../components/Counter';
import { Users, AlertTriangle } from 'lucide-react';
import { useGymData } from '../hooks/useGymData';

export function Dashboard() {
  const [currentCount, setCurrentCount] = useState(0);
  const [showAlert, setShowAlert] = useState(false);
  const [isSystemActive, setIsSystemActive] = useState(true);
  const MAX_CAPACITY = 40;
  const { addEntry, addExit } = useGymData();

  // Simular lecturas automáticas del sistema de visión computarizada
  useEffect(() => {
    if (!isSystemActive) return;

    const interval = setInterval(() => {
      // Simular cambios aleatorios en el conteo (-1, 0, o +1)
      const change = Math.floor(Math.random() * 3) - 1; // -1, 0, o 1
      setCurrentCount((prev) => {
        const newCount = Math.max(0, prev + change);
        
        // Registrar entrada o salida
        if (change === 1) {
          addEntry();
        } else if (change === -1 && prev > 0) {
          addExit();
        }
        
        // Limitar a un máximo razonable (por ejemplo, 60)
        return Math.min(60, newCount);
      });
    }, 2000); // Actualizar cada 2 segundos

    return () => clearInterval(interval);
  }, [isSystemActive, addEntry, addExit]);

  // Monitorear si se excede la capacidad
  useEffect(() => {
    if (currentCount > MAX_CAPACITY) {
      setShowAlert(true);
    } else {
      setShowAlert(false);
    }
  }, [currentCount]);

  const getCapacityPercentage = () => {
    return (currentCount / MAX_CAPACITY) * 100;
  };

  const handleToggleSystem = () => {
    setIsSystemActive(!isSystemActive);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-2">
          <Users className="w-10 h-10 text-white" />
          <h1 className="text-4xl font-bold text-white">Contador de personas</h1>
        </div>
        <p className="text-blue-200">Capacidad máxima recomendada: {MAX_CAPACITY} personas</p>
        <div className="flex items-center justify-center gap-2 mt-2">
          <div className={`w-3 h-3 rounded-full ${isSystemActive ? 'bg-green-400 animate-pulse' : 'bg-gray-400'}`} />
          <span className="text-sm text-blue-200">
            Sistema de visión computarizada: {isSystemActive ? 'ACTIVO' : 'PAUSADO'}
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
                Se ha superado el límite de {MAX_CAPACITY} personas. 
                Exceso: {currentCount - MAX_CAPACITY} personas
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Control Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Counter Section */}
        <div className="bg-white/10 backdrop-blur-md rounded-xl shadow-lg p-8 border border-white/20">
          <Counter
            count={currentCount}
            maxCapacity={MAX_CAPACITY}
            isSystemActive={isSystemActive}
            onToggleSystem={handleToggleSystem}
          />
        </div>

        {/* Traffic Light Section */}
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
