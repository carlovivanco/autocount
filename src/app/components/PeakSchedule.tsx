import { TrendingUp, TrendingDown } from 'lucide-react';
import type { PeakSchedule } from '../hooks/useCounterWebSocket';

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];

function toRanges(hours: number[]): string {
  if (!hours.length) return '';
  const sorted = [...hours].sort((a, b) => a - b);
  const ranges: string[] = [];
  let start = sorted[0];
  let prev = sorted[0];
  for (let i = 1; i <= sorted.length; i++) {
    if (i === sorted.length || sorted[i] !== prev + 1) {
      ranges.push(start === prev ? `${start}:00` : `${start}:00–${prev + 1}:00`);
      if (i < sorted.length) { start = sorted[i]; prev = sorted[i]; }
    } else { prev = sorted[i]; }
  }
  return ranges.join(', ');
}

export function PeakScheduleCard({ schedule }: { schedule: PeakSchedule }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-5">
        <TrendingUp className="w-5 h-5 text-[#7EC8E3]" />
        <h3 className="text-white font-semibold">Horarios Peak · Predicción IA</h3>
      </div>

      <div className="space-y-3">
        {DIAS.map((dia) => {
          const peak = schedule[dia] ?? [];
          const ranges = toRanges(peak);
          return (
            <div key={dia} className="flex items-start gap-3">
              <span className="text-white/50 text-sm w-24 shrink-0 pt-0.5">{dia}</span>
              <div className="flex-1 flex flex-wrap gap-1">
                {peak.length > 0 ? (
                  <span className="inline-flex items-center gap-1 text-xs bg-red-500/15 border border-red-400/25 text-red-300 rounded-lg px-2 py-1">
                    <TrendingUp className="w-3 h-3" /> Peak: {ranges}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs bg-sky-500/15 border border-sky-400/25 text-sky-300 rounded-lg px-2 py-1">
                    <TrendingDown className="w-3 h-3" /> Off-peak todo el día
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-white/30 text-xs mt-4 leading-relaxed">
        Predicción basada en datos históricos del gimnasio · Se actualiza automáticamente cada 30 días
      </p>
    </div>
  );
}
