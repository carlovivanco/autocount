import { Video, Circle } from 'lucide-react';
import { useState, useEffect } from 'react';

interface CameraFeedProps {
  title: string;
  cameraId: string;
}

export function CameraFeed({ title, cameraId }: CameraFeedProps) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => {
      setTime(new Date());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <div className="border border-white/30 rounded-lg overflow-hidden">
      {/* Camera Header */}
      <div className="bg-blue-950/80 backdrop-blur-sm text-white px-4 py-3 flex items-center justify-between border-b border-white/20">
        <div className="flex items-center gap-2">
          <Video className="w-5 h-5" />
          <span className="font-semibold">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          <Circle className="w-3 h-3 fill-red-400 text-red-400 animate-pulse" />
          <span className="text-sm">EN VIVO</span>
        </div>
      </div>

      {/* Camera Feed Placeholder */}
      <div className="relative aspect-video bg-gray-800 flex items-center justify-center">
        {/* Simulated camera feed - placeholder */}
        <div className="absolute inset-0 bg-gradient-to-br from-gray-700 to-gray-900">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-gray-400">
              <Video className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-sm">Cámara {cameraId}</p>
              <p className="text-xs mt-2">Feed de video en tiempo real</p>
            </div>
          </div>
          
          {/* Timestamp Overlay */}
          <div className="absolute bottom-4 left-4 bg-black/70 px-3 py-2 rounded text-white text-sm font-mono">
            <div>{formatDate(time)}</div>
            <div className="text-xl">{formatTime(time)}</div>
          </div>

          {/* Camera ID Overlay */}
          <div className="absolute top-4 right-4 bg-black/70 px-3 py-1 rounded text-white text-xs font-mono">
            CAM-{cameraId.toUpperCase()}
          </div>
        </div>
      </div>
    </div>
  );
}