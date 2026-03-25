import { useState, useCallback } from 'react';

interface LogEntry {
  type: 'entrada' | 'salida';
  timestamp: Date;
}

// Singleton para compartir estado entre páginas
let sharedState = {
  totalEntries: 0,
  totalExits: 0,
  entries: [] as LogEntry[],
};

export function useGymData() {
  const [, forceUpdate] = useState({});

  const addEntry = useCallback(() => {
    sharedState.totalEntries++;
    sharedState.entries.push({
      type: 'entrada',
      timestamp: new Date(),
    });
    forceUpdate({});
  }, []);

  const addExit = useCallback(() => {
    sharedState.totalExits++;
    sharedState.entries.push({
      type: 'salida',
      timestamp: new Date(),
    });
    forceUpdate({});
  }, []);

  return {
    totalEntries: sharedState.totalEntries,
    totalExits: sharedState.totalExits,
    entries: sharedState.entries,
    addEntry,
    addExit,
  };
}
