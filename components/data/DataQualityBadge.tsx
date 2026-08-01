import React from 'react';
import { ShieldCheck, AlertTriangle } from 'lucide-react';

export function DataQualityBadge({ score, qualityStatus, events }: { score: number; qualityStatus: string; events: any[] }) {
  const isHealthy = score >= 0.85;

  return (
    <div className="flex items-center space-x-2 font-mono text-xs bg-[var(--bg-primary)] px-2.5 py-1 rounded border border-[var(--border-subtle)]">
      {isHealthy ? (
        <ShieldCheck className="w-3.5 h-3.5 text-[var(--positive)]" />
      ) : (
        <AlertTriangle className="w-3.5 h-3.5 text-[var(--warning)]" />
      )}
      <span className="text-gray-300">DATA QUALITY:</span>
      <span className={isHealthy ? "text-[var(--positive)] font-bold" : "text-[var(--warning)] font-bold"}>
        {(score * 100).toFixed(0)}%
      </span>
      <span className="text-gray-600">|</span>
      <span className="text-gray-400 uppercase">{qualityStatus}</span>
    </div>
  );
}