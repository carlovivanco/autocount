interface TrafficLightProps {
  percentage: number;
  currentCount: number;
  maxCapacity: number;
}

export function TrafficLight({ percentage, currentCount, maxCapacity }: TrafficLightProps) {
  const getStatus = () => {
    if (percentage < 66.7) return 'green';
    if (percentage < 100) return 'yellow';
    if (percentage <= 100) return 'red';
    return 'critical'; // percentage > 100
  };

  const status = getStatus();

  const getStatusText = () => {
    if (status === 'green') return 'Espacio Disponible';
    if (status === 'yellow') return 'Llenándose';
    if (status === 'red') return 'Capacidad Llena';
    return '¡CAPACIDAD EXCEDIDA!';
  };

  const getStatusMessage = () => {
    if (status === 'green') return 'Puedes ingresar sin problema';
    if (status === 'yellow') return 'El gimnasio se está llenando';
    if (status === 'red') return 'Considera regresar más tarde';
    return 'Se ha superado la capacidad máxima';
  };

  return (
    <div className="flex flex-col items-center">
      <h2 className="text-xl font-bold text-white mb-6">Estado de Capacidad</h2>

      {/* Traffic Light */}
      <div className="bg-[#0D1117] rounded-3xl px-8 py-6 mb-6 shadow-2xl border border-white/10">
        <div className="flex flex-col gap-5 items-center">
          {/* Red */}
          <div
            className={`w-20 h-20 rounded-full border-4 border-[#1a1f2e] transition-all duration-500 ${
              status === 'red' || status === 'critical'
                ? 'bg-red-600 shadow-[0_0_35px_rgba(220,38,38,0.85)]'
                : 'bg-red-950/60'
            } ${status === 'critical' ? 'animate-pulse' : ''}`}
          />
          {/* Yellow */}
          <div
            className={`w-20 h-20 rounded-full border-4 border-[#1a1f2e] transition-all duration-500 ${
              status === 'yellow'
                ? 'bg-yellow-400 shadow-[0_0_35px_rgba(234,179,8,0.85)]'
                : 'bg-yellow-950/60'
            }`}
          />
          {/* Green */}
          <div
            className={`w-20 h-20 rounded-full border-4 border-[#1a1f2e] transition-all duration-500 ${
              status === 'green'
                ? 'bg-green-500 shadow-[0_0_35px_rgba(34,197,94,0.85)]'
                : 'bg-green-950/60'
            }`}
          />
        </div>
      </div>

      {/* Status Info */}
      <div className="text-center w-full">
        <div className={`text-2xl font-bold mb-1 ${
          status === 'green' ? 'text-green-400' :
          status === 'yellow' ? 'text-yellow-300' :
          status === 'red' ? 'text-red-400' :
          'text-red-400 animate-pulse'
        }`}>
          {getStatusText()}
        </div>
        <p className="text-white/50 text-sm mb-5">
          {getStatusMessage()}
        </p>

        {/* Occupancy box */}
        <div className={`rounded-xl p-4 inline-block w-full ${
          status === 'critical'
            ? 'bg-red-500/20 border-2 border-red-400/50'
            : 'bg-white/8 border border-white/15'
        }`}>
          <div className="text-xs text-white/40 uppercase tracking-wide mb-1">Ocupación actual</div>
          <div className={`text-4xl font-black tabular-nums ${
            status === 'critical' ? 'text-red-300' : 'text-white'
          }`}>
            {currentCount}
            <span className="text-xl font-normal text-white/40"> / {maxCapacity}</span>
          </div>
          {status === 'critical' && (
            <div className="text-xs text-red-300 mt-2 font-semibold">
              ¡Acceso restringido — avisa al personal!
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
