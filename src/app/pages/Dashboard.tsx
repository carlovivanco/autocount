import { useState, useEffect, useCallback, useRef } from 'react';
import { PeakScheduleCard } from '../components/PeakSchedule';
import { AlertTriangle, Clock, Activity, TrendingUp, TrendingDown } from 'lucide-react';
import { useCounterWebSocket } from '../hooks/useCounterWebSocket';

const MAX_CAPACITY = 60;

// Gauge geometry — 270° arc, gap at the bottom
const R     = 80;
const CIRC  = 2 * Math.PI * R;  // ≈ 502.65
const ARC   = CIRC * 0.75;      // ≈ 376.99  (270° of circumference)

function gaugeColor(pct: number) {
  if (pct <= 66.7) return '#22c55e';
  if (pct < 100)   return '#f59e0b';
  return '#ef4444';
}

function gaugeGlow(pct: number) {
  if (pct <= 66.7) return 'rgba(34,197,94,0.45)';
  if (pct < 100)   return 'rgba(245,158,11,0.45)';
  return 'rgba(239,68,68,0.45)';
}

function gaugeStatus(pct: number): { label: string; sub: string } {
  if (pct < 66.7) return { label: 'Espacio disponible',   sub: 'Puedes ingresar sin problema' };
  if (pct < 85)   return { label: 'Llenándose',            sub: 'El gimnasio se está llenando' };
  if (pct < 100)  return { label: 'Casi lleno',            sub: 'Espacio limitado disponible' };
  if (pct <= 100) return { label: 'Capacidad máxima',      sub: 'Considera regresar más tarde' };
  return                  { label: '¡Capacidad excedida!', sub: 'Notifica al personal del gimnasio' };
}

export function Dashboard() {
  const [currentCount, setCurrentCount] = useState(0);
  const [trend, setTrend]               = useState<'up' | 'down' | 'stable'>('stable');
  const prevCountRef  = useRef(0);
  const trendTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { count: wsCount, connected: wsConnected, peakPrediction, peakSchedule } =
    useCounterWebSocket(useCallback(() => {}, []));

  useEffect(() => {
    if (!wsConnected) return;
    if (wsCount !== prevCountRef.current) {
      setTrend(wsCount > prevCountRef.current ? 'up' : 'down');
      if (trendTimerRef.current) clearTimeout(trendTimerRef.current);
      trendTimerRef.current = setTimeout(() => setTrend('stable'), 2500);
    }
    prevCountRef.current = wsCount;
    setCurrentCount(wsCount);
  }, [wsCount, wsConnected]);

  useEffect(() => () => { if (trendTimerRef.current) clearTimeout(trendTimerRef.current); }, []);

  const pct        = (currentCount / MAX_CAPACITY) * 100;
  const color      = gaugeColor(pct);
  const glow       = gaugeGlow(pct);
  const status     = gaugeStatus(pct);
  const available  = Math.max(0, MAX_CAPACITY - currentCount);
  const over       = pct > 100;
  const fillOffset = ARC * Math.max(0, 1 - Math.min(pct / 100, 1));

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">

      {/* ── Header ─────────────────────────────────── */}
      <div className="text-center mb-8">
        <p className="text-[#7EC8E3] text-xs font-semibold uppercase tracking-[0.2em] mb-2">
          Tecnológico de Monterrey · Campus Estado de México
        </p>
        <h1 className="text-3xl md:text-4xl font-bold text-white mb-4">
          Aforo del Gimnasio
        </h1>

        <div className="flex flex-wrap items-center justify-center gap-2">
          <span className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full font-medium border ${
            wsConnected
              ? 'bg-emerald-500/15 border-emerald-400/30 text-emerald-300'
              : 'bg-amber-500/15  border-amber-400/30  text-amber-300'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            {wsConnected ? 'Raspberry Pi conectada' : 'Sin conexión'}
          </span>

          {peakPrediction && (
            <span className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full font-medium border ${
              peakPrediction === 'Peak'
                ? 'bg-orange-500/15 border-orange-400/30 text-orange-300'
                : 'bg-sky-500/15   border-sky-400/30   text-sky-300'
            }`}>
              {peakPrediction === 'Peak'
                ? <TrendingUp  className="w-3 h-3" />
                : <TrendingDown className="w-3 h-3" />}
              {peakPrediction === 'Peak' ? 'Hora Peak' : 'Hora Off-peak'}
            </span>
          )}
        </div>
      </div>

      {/* ── Alert Banner ───────────────────────────── */}
      {over && (
        <div className="mb-6 rounded-2xl border border-red-400/40 bg-red-500/10 p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 flex-shrink-0 rounded-xl bg-red-500/20 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className="font-semibold text-red-300 text-sm">¡Capacidad excedida!</p>
              <p className="text-xs text-red-400/70 mt-0.5">
                Límite de {MAX_CAPACITY} personas superado · Exceso:{' '}
                {currentCount - MAX_CAPACITY} persona{currentCount - MAX_CAPACITY !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Hero Panel ─────────────────────────────── */}
      <div className="bg-white/[0.05] backdrop-blur-md rounded-3xl border border-white/10 p-6 md:p-10 mb-6 shadow-2xl">
        <div className="flex flex-col md:flex-row items-center gap-8 md:gap-12">

          {/* Circular gauge */}
          <div className="flex-shrink-0 flex flex-col items-center gap-1">
            <svg
              width="220" height="200"
              viewBox="0 0 240 210"
              aria-label={`${currentCount} de ${MAX_CAPACITY} personas, ${Math.round(pct)}% de capacidad`}
            >
              {/* Background track */}
              <circle
                cx="120" cy="115" r={R}
                fill="none"
                stroke="rgba(255,255,255,0.06)"
                strokeWidth="15"
                strokeLinecap="round"
                strokeDasharray={`${ARC} ${CIRC}`}
                transform="rotate(-225 120 115)"
              />
              {/* Progress arc */}
              <circle
                cx="120" cy="115" r={R}
                fill="none"
                stroke={color}
                strokeWidth="15"
                strokeLinecap="round"
                strokeDasharray={`${ARC} ${CIRC}`}
                strokeDashoffset={fillOffset}
                transform="rotate(-225 120 115)"
                style={{
                  transition: 'stroke-dashoffset 0.7s cubic-bezier(0.4,0,0.2,1), stroke 0.5s ease',
                  filter: `drop-shadow(0 0 10px ${glow})`,
                }}
              />

              {/* Trend arrow */}
              {trend !== 'stable' && (
                <text
                  x="120" y="66"
                  textAnchor="middle"
                  fill={trend === 'up' ? '#4ade80' : '#f87171'}
                  fontSize="14" fontWeight="700"
                >
                  {trend === 'up' ? '▲' : '▼'}
                </text>
              )}

              {/* Count */}
              <text
                x="120" y="122"
                textAnchor="middle"
                dominantBaseline="middle"
                fill="white"
                fontSize="56"
                fontWeight="900"
                fontFamily="system-ui, -apple-system, sans-serif"
                style={{ letterSpacing: '-2px' }}
              >
                {currentCount}
              </text>

              {/* Subtitle */}
              <text
                x="120" y="148"
                textAnchor="middle"
                fill="rgba(255,255,255,0.35)"
                fontSize="13"
                fontFamily="system-ui, -apple-system, sans-serif"
              >
                de {MAX_CAPACITY} personas
              </text>
            </svg>

            <p className="text-sm font-semibold tabular-nums" style={{ color }}>
              {Math.round(pct)}% de capacidad
            </p>
          </div>

          {/* Status + stats */}
          <div className="flex-1 w-full min-w-0">
            <div className="mb-6">
              <h2 className="text-2xl font-bold mb-1" style={{ color }}>
                {status.label}
              </h2>
              <p className="text-white/50 text-sm">{status.sub}</p>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="rounded-2xl bg-white/[0.04] border border-white/[0.07] p-4">
                <p className="text-white/40 text-xs uppercase tracking-wider mb-2">Adentro</p>
                <p className="text-white text-2xl font-black tabular-nums leading-none">
                  {currentCount}
                </p>
              </div>
              <div className="rounded-2xl bg-white/[0.04] border border-white/[0.07] p-4">
                <p className="text-white/40 text-xs uppercase tracking-wider mb-2">
                  {over ? 'Exceso' : 'Libres'}
                </p>
                <p className={`text-2xl font-black tabular-nums leading-none ${
                  over ? 'text-red-400' : 'text-emerald-400'
                }`}>
                  {over ? `+${currentCount - MAX_CAPACITY}` : available}
                </p>
              </div>
              <div className="rounded-2xl bg-white/[0.04] border border-white/[0.07] p-4">
                <p className="text-white/40 text-xs uppercase tracking-wider mb-2">Máximo</p>
                <p className="text-white/50 text-2xl font-black tabular-nums leading-none">
                  {MAX_CAPACITY}
                </p>
              </div>
            </div>

            <div className="h-1.5 bg-white/[0.07] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.min(100, pct)}%`,
                  backgroundColor: color,
                  boxShadow: `0 0 8px ${glow}`,
                  transition: 'width 0.7s cubic-bezier(0.4,0,0.2,1), background-color 0.5s ease',
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── Peak Schedule ──────────────────────────── */}
      {peakSchedule && (
        <div className="bg-white/[0.05] backdrop-blur-md rounded-3xl border border-white/10 p-6 mb-6">
          <PeakScheduleCard schedule={peakSchedule} />
        </div>
      )}

      {/* ── Info Row ───────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

        <div className="bg-white/[0.05] backdrop-blur-md rounded-3xl border border-white/10 p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 rounded-xl bg-[#7EC8E3]/10 flex items-center justify-center">
              <Clock className="w-4 h-4 text-[#7EC8E3]" />
            </div>
            <h3 className="text-white font-semibold">Horarios de Operación</h3>
          </div>
          <div className="space-y-0">
            {[
              { day: 'Lunes – Viernes', hours: '6:00 – 21:00', closed: false },
              { day: 'Sábado',          hours: '8:00 – 12:00', closed: false },
              { day: 'Domingo',         hours: 'Cerrado',       closed: true  },
            ].map(({ day, hours, closed }) => (
              <div
                key={day}
                className="flex justify-between items-center py-2.5 border-b border-white/[0.06] last:border-0"
              >
                <span className="text-white/50 text-sm">{day}</span>
                <span className={`text-sm font-medium ${closed ? 'text-white/25' : 'text-white'}`}>
                  {hours}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white/[0.05] backdrop-blur-md rounded-3xl border border-white/10 p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 rounded-xl bg-[#7EC8E3]/10 flex items-center justify-center">
              <Activity className="w-4 h-4 text-[#7EC8E3]" />
            </div>
            <h3 className="text-white font-semibold">Acerca del Sistema</h3>
          </div>
          <p className="text-white/50 text-sm leading-relaxed mb-4">
            Conteo actualizado en tiempo real mediante visión computarizada con IA instalada en la entrada del gimnasio.
          </p>
          <div className="flex flex-wrap gap-2 mb-4">
            {['Raspberry Pi 5', 'IMX500', 'YOLO11n'].map((tag) => (
              <span
                key={tag}
                className="text-xs px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/35"
              >
                {tag}
              </span>
            ))}
          </div>
          <p className="text-white/25 text-xs">
            ¿Dudas? Contacta a Servicios Deportivos · Ext. 4200
          </p>
        </div>

      </div>
    </div>
  );
}
