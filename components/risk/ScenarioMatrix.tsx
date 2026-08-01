import React from 'react';

export function ScenarioMatrix({ scenarios }: { scenarios: any }) {
  return (
    <div className="terminal-panel rounded p-4 space-y-4">
      <div className="text-xs font-semibold text-[var(--text-secondary)] tracking-wider flex justify-between items-center border-b border-[var(--border-subtle)] pb-2">
        <span>INVESTMENT COMMITTEE SCENARIO MATRIX</span>
        <span className="text-[10px] font-mono text-[var(--text-muted)]">PROBABILITY-WEIGHTED MODEL</span>
      </div>

      <div className="grid grid-cols-3 gap-3 font-mono text-xs">
        {/* Bull Case */}
        <div className="bg-[var(--bg-primary)] p-3 rounded border border-[var(--border-subtle)]">
          <div className="text-[var(--positive)] font-bold mb-1">BULL CASE</div>
          <div className="text-gray-400 text-[10px] mb-2">Prob: {scenarios.bull_case.probability_pct}%</div>
          <div className="text-sm font-bold tabular-data text-white">+{scenarios.bull_case.price_movement_estimate_pct}%</div>
          <p className="text-[10px] text-gray-400 mt-2 font-sans line-clamp-2">{scenarios.bull_case.narrative_trigger}</p>
        </div>

        {/* Base Case */}
        <div className="bg-[var(--bg-primary)] p-3 rounded border border-[var(--border-subtle)]">
          <div className="text-blue-400 font-bold mb-1">BASE CASE</div>
          <div className="text-gray-400 text-[10px] mb-2">Prob: {scenarios.base_case.probability_pct}%</div>
          <div className="text-sm font-bold tabular-data text-white">{scenarios.base_case.price_movement_estimate_pct > 0 ? `+${scenarios.base_case.price_movement_estimate_pct}%` : `${scenarios.base_case.price_movement_estimate_pct}%`}</div>
          <p className="text-[10px] text-gray-400 mt-2 font-sans line-clamp-2">{scenarios.base_case.narrative_trigger}</p>
        </div>

        {/* Bear Case */}
        <div className="bg-[var(--bg-primary)] p-3 rounded border border-[var(--border-subtle)]">
          <div className="text-[var(--negative)] font-bold mb-1">BEAR CASE</div>
          <div className="text-gray-400 text-[10px] mb-2">Prob: {scenarios.bear_case.probability_pct}%</div>
          <div className="text-sm font-bold tabular-data text-white">{scenarios.bear_case.price_movement_estimate_pct}%</div>
          <p className="text-[10px] text-gray-400 mt-2 font-sans line-clamp-2">{scenarios.bear_case.narrative_trigger}</p>
        </div>
      </div>
    </div>
  );
}