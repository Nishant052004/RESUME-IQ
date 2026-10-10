export default function ScoreRing({ score, size = 56, stroke = 5 }) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference * (1 - clamped / 100);
  const color = clamped >= 70 ? "var(--success)" : clamped >= 40 ? "var(--primary)" : "var(--warn)";
  return (
    <div className="ring" style={{ width: size, height: size }} title={`Match score: ${score}`}>
      <svg width={size} height={size}>
        <circle className="track" cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} />
        <circle
          className="bar"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ stroke: color }}
        />
      </svg>
      <div className="value">{Math.round(clamped)}%</div>
    </div>
  );
}
