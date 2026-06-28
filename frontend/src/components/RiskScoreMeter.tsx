import { riskBand } from "../lib/risk";

interface RiskScoreMeterProps {
  score: number;
  size?: number;
}

// SVG circular gauge. Color + label come from riskBand() thresholds:
//   0-30 green | 31-60 amber | 61-80 red | 81-100 dark red.
export function RiskScoreMeter({ score, size = 200 }: RiskScoreMeterProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const band = riskBand(clamped);

  const stroke = 16;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);
  const center = size / 2;

  return (
    <div className="flex flex-col items-center" role="img" aria-label={`Risk score ${clamped} out of 100, ${band.label}`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={stroke}
        />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={band.color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="-mt-[60%] flex flex-col items-center">
        <span className="text-5xl font-bold tabular-nums text-slate-900">
          {clamped}
        </span>
        <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
          / 100
        </span>
        <span
          className={`mt-2 rounded-full px-3 py-1 text-sm font-semibold ${band.bgClass} ${band.textClass}`}
        >
          {band.label}
        </span>
      </div>
    </div>
  );
}
