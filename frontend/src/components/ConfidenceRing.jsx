import { useEffect, useRef } from 'react';
import gsap from 'gsap';

/**
 * SVG donut ring that animates from 0 to `value` (0-1).
 * Used for confidence percentages in the Brief page.
 */
export default function ConfidenceRing({ value = 0, size = 72, color = 'var(--color-accent)', label }) {
  const fillRef = useRef(null);
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    if (!fillRef.current) return;
    gsap.fromTo(
      fillRef.current,
      { strokeDashoffset: circumference },
      {
        strokeDashoffset: circumference * (1 - value),
        duration: 1.4,
        delay: 0.3,
        ease: 'power3.out',
      }
    );
  }, [value, circumference]);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className="ring-track"
          />
          <circle
            ref={fillRef}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className="ring-fill"
            stroke={color}
            strokeDasharray={circumference}
            strokeDashoffset={circumference}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-mono text-sm font-medium tabular-nums" style={{ color }}>
            {Math.round(value * 100)}
          </span>
        </div>
      </div>
      {label && <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">{label}</span>}
    </div>
  );
}
