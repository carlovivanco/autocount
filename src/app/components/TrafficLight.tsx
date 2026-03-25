interface TrafficLightProps {
  percentage: number;
  currentCount: number;
  maxCapacity: number;
}

export function TrafficLight({ percentage, currentCount, maxCapacity }: TrafficLightProps) {
  const getStatus = () => {
    if (percentage < 65) return 'green';
    if (percentage < 90) return 'yellow';
    if (percentage <= 100) return 'red';
    return 'critical';
  };

  const status = getStatus();

  const getStatusText = () => {
    if (status === 'green') return 'Capacidad Disponible';
    if (status === 'yellow') return 'Capacidad Media';
    if (status === 'red') return 'Capacidad Llena';
    return '¡CAPACIDAD EXCEDIDA!';
  };

  const getStatusMessage = () => {
    if (status === 'green') return 'El gimnasio tiene suficiente espacio disponible';
    if (status === 'yellow') return 'El gimnasio se está llenando';
    if (status === 'red') return 'El gimnasio está al máximo de capacidad';
    return 'Se ha superado la capacidad máxima recomendada';
  };

  return (
    <div className="flex flex-col items-center">
      <h2 className="text-2xl font-bold text-white mb-6">Estado de Capacidad</h2>
      
      {/* Traffic Light */}
      <div className="bg-gray-900 rounded-3xl p-6 mb-6 shadow-2xl">
        <div className="flex flex-col gap-4">
          {/* Red Light */}
          <div
            className={`w-24 h-24 rounded-full border-4 border-gray-700 transition-all duration-300 ${
              status === 'red' || status === 'critical'
                ? 'bg-red-600 shadow-[0_0_30px_rgba(220,38,38,0.8)]'
                : 'bg-red-950 opacity-30'
            } ${status === 'critical' ? 'animate-pulse' : ''}`}
          />
          
          {/* Yellow Light */}
          <div
            className={`w-24 h-24 rounded-full border-4 border-gray-700 transition-all duration-300 ${
              status === 'yellow'
                ? 'bg-yellow-400 shadow-[0_0_30px_rgba(234,179,8,0.8)]'
                : 'bg-yellow-950 opacity-30'
            }`}
          />
          
          {/* Green Light */}
          <div
            className={`w-24 h-24 rounded-full border-4 border-gray-700 transition-all duration-300 ${
              status === 'green'
                ? 'bg-green-500 shadow-[0_0_30px_rgba(34,197,94,0.8)]'
                : 'bg-green-950 opacity-30'
            }`}
          />
        </div>
      </div>

      {/* Status Information */}
      <div className="text-center">
        <div className={`text-2xl font-bold mb-2 ${
          status === 'green' ? 'text-green-300' :
          status === 'yellow' ? 'text-yellow-300' :
          status === 'red' ? 'text-red-300' :
          'text-red-400 animate-pulse'
        }`}>
          {getStatusText()}
        </div>
        <p className="text-blue-200 mb-4">
          {getStatusMessage()}
        </p>
        <div className={`rounded-lg p-4 inline-block ${
          status === 'critical' ? 'bg-red-500/30 border-2 border-red-400' : 'bg-white/10 border border-white/20'
        }`}>
          <div className="text-sm text-blue-200 mb-1">Ocupación actual</div>
          <div className={`text-3xl font-bold ${
            status === 'critical' ? 'text-red-200' : 'text-white'
          }`}>
            {currentCount} / {maxCapacity}
          </div>
          {status === 'critical' && (
            <div className="text-xs text-red-200 mt-2 font-semibold">
              ¡Atención requerida!
            </div>
          )}
        </div>
      </div>
    </div>
  );
}