import { useRef, useEffect } from 'react';
import { motion } from 'motion/react';
import TickerInput from '../components/TickerInput';

export default function Home() {
  const gridRef = useRef(null);

  // Subtle animated dot grid in background
  useEffect(() => {
    const canvas = gridRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = (t) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const spacing = 48;
      const cols = Math.ceil(canvas.width / spacing);
      const rows = Math.ceil(canvas.height / spacing);
      const cx = canvas.width / 2;
      const cy = canvas.height / 2;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const x = c * spacing + spacing / 2;
          const y = r * spacing + spacing / 2;
          const dist = Math.hypot(x - cx, y - cy);
          const maxDist = Math.hypot(cx, cy);
          const pulse = Math.sin(t * 0.0008 - dist * 0.004) * 0.5 + 0.5;
          const alpha = (1 - dist / maxDist) * 0.12 * pulse + 0.02;

          ctx.beginPath();
          ctx.arc(x, y, 1, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(52, 211, 153, ${alpha})`;
          ctx.fill();
        }
      }
      animId = requestAnimationFrame(draw);
    };
    animId = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <div className="relative min-h-[100dvh] flex overflow-hidden">
      {/* Canvas dot grid */}
      <canvas ref={gridRef} className="absolute inset-0 pointer-events-none" />

      {/* Radial vignette */}
      <div className="absolute inset-0 pointer-events-none" style={{
        background: 'radial-gradient(ellipse 60% 50% at 50% 45%, transparent 0%, var(--color-bg-primary) 100%)',
      }} />

      {/* Content — asymmetric split: left-heavy text, right breathing room */}
      <div className="relative z-10 flex flex-col justify-center w-full max-w-6xl mx-auto px-8 md:px-16 py-24">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12 items-center min-h-[70dvh]">

          {/* Left: Hero copy */}
          <div className="md:col-span-7 flex flex-col gap-8">
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-border-primary bg-bg-secondary/60 backdrop-blur-sm mb-8">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
                </span>
                <span className="text-[11px] font-mono font-medium text-text-muted uppercase tracking-wider">Live Intelligence</span>
              </div>

              <h1 className="text-4xl md:text-6xl font-semibold tracking-tighter leading-none text-text-primary mb-6">
                Pre-earnings
                <br />
                <span className="text-accent">clarity,</span> not noise.
              </h1>

              <p className="text-base md:text-lg text-text-secondary leading-relaxed max-w-[52ch]">
                Three data sources. Six reasoning calls. One analyst-grade brief
                with contradiction resolution, scenario analysis, and historical
                pattern matching — delivered in under 37 seconds.
              </p>
            </motion.div>

            <TickerInput />
          </div>

          {/* Right: Data provenance column */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 1 }}
            className="md:col-span-5 hidden md:flex flex-col gap-6 pl-8 border-l border-border-subtle"
          >
            {[
              { label: 'SEC EDGAR', desc: '10-Q / 10-K filings', authority: '1.00' },
              { label: 'BRIGHT DATA', desc: 'SERP + Web Unlocker', authority: '0.85' },
              { label: 'YFINANCE', desc: 'Consensus EPS, P/E, PEG', authority: '0.90' },
            ].map((source, i) => (
              <motion.div
                key={source.label}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.8 + i * 0.12, duration: 0.5 }}
                className="group"
              >
                <div className="flex items-baseline justify-between mb-1">
                  <span className="text-[11px] font-mono font-medium text-text-primary tracking-wider uppercase">{source.label}</span>
                  <span className="text-[10px] font-mono text-text-muted tabular-nums">{source.authority}</span>
                </div>
                <p className="text-[13px] text-text-muted leading-relaxed">{source.desc}</p>
                <div className="mt-3 h-px w-full bg-border-subtle group-last:hidden" />
              </motion.div>
            ))}

            <div className="mt-4 flex items-center gap-3">
              <div className="h-px flex-1 bg-border-subtle" />
              <span className="text-[10px] font-mono text-text-muted/40 uppercase tracking-widest">Authority Scores</span>
              <div className="h-px flex-1 bg-border-subtle" />
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
