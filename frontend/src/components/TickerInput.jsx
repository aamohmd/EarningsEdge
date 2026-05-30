import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import gsap from 'gsap';

export default function TickerInput() {
  const [ticker, setTicker] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const containerRef = useRef(null);

  // GSAP focus glow — inner border, not outer neon
  useEffect(() => {
    if (!containerRef.current) return;
    if (isFocused) {
      gsap.to(containerRef.current, {
        borderColor: 'var(--color-accent)',
        boxShadow: 'inset 0 1px 0 0 oklch(0.72 0.15 163 / 0.08), 0 0 0 1px oklch(0.72 0.15 163 / 0.12)',
        duration: 0.35,
        ease: 'power2.out',
      });
    } else {
      gsap.to(containerRef.current, {
        borderColor: 'var(--color-border-primary)',
        boxShadow: 'inset 0 1px 0 0 oklch(1 0 0 / 0.03)',
        duration: 0.35,
        ease: 'power2.out',
      });
    }
  }, [isFocused]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const t = ticker.trim().toUpperCase();
    if (t.length > 0) navigate(`/brief/${t}`);
  };

  const quickTickers = ['NVDA', 'TSLA', 'AMD'];

  return (
    <motion.form
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
      onSubmit={handleSubmit}
      className="w-full max-w-lg"
    >
      {/* Terminal-style prompt */}
      <div
        ref={containerRef}
        className="relative flex items-center bg-bg-secondary border border-border-primary rounded-lg overflow-hidden inner-light"
      >
        <span className="pl-5 font-mono text-sm text-text-muted select-none shrink-0">$</span>

        <input
          ref={inputRef}
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="TICKER"
          className="flex-1 bg-transparent border-none outline-none text-text-primary caret-accent pl-3 pr-4 py-4 font-mono text-base tracking-[0.2em] placeholder:text-text-muted/30 uppercase"
          autoFocus
          maxLength={5}
          spellCheck={false}
          autoComplete="off"
        />

        <button
          type="submit"
          disabled={!ticker.trim()}
          className="px-5 py-4 font-mono text-xs font-medium text-text-muted hover:text-accent disabled:text-border-hover transition-colors uppercase tracking-wider"
        >
          Run →
        </button>
      </div>

      {/* Quick-select chips */}
      <div className="mt-5 flex items-center gap-3">
        <span className="text-[11px] text-text-muted/40 font-mono uppercase tracking-wider">Cached</span>
        <div className="h-px flex-1 bg-border-subtle" />
        <div className="flex gap-2">
          {quickTickers.map((t, i) => (
            <motion.button
              key={t}
              type="button"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + i * 0.08, duration: 0.4 }}
              onClick={() => navigate(`/brief/${t}`)}
              className="px-3 py-1 text-[11px] font-mono font-medium rounded-md
                border border-border-primary text-text-muted
                hover:text-accent hover:border-accent-border hover:bg-accent-dim
                active:translate-y-px
                transition-all duration-150"
            >
              {t}
            </motion.button>
          ))}
        </div>
      </div>
    </motion.form>
  );
}
