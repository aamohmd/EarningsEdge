import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import gsap from 'gsap';

const PIPELINE_STEPS = [
  { id: 'fetch-sec',   label: 'SEC EDGAR 10-Q',              group: 'fetch',   duration: 2800 },
  { id: 'fetch-serp',  label: 'Bright Data SERP API',        group: 'fetch',   duration: 3200 },
  { id: 'fetch-web',   label: 'Web Unlocker (full articles)', group: 'fetch',   duration: 4200 },
  { id: 'fetch-yfi',   label: 'yFinance quantitative',       group: 'fetch',   duration: 1800 },
  { id: 'pre-synth',   label: 'Dedup + recency filter',      group: 'process', duration: 1400 },
  { id: 'call-0',      label: 'Contradiction detection',     group: 'reason',  duration: 3800 },
  { id: 'call-1',      label: 'Signal classification',       group: 'reason',  duration: 2600 },
  { id: 'call-2',      label: 'Authority resolution',        group: 'reason',  duration: 3200 },
  { id: 'call-3',      label: 'Section drafting',            group: 'reason',  duration: 4200 },
  { id: 'call-5',      label: 'Contract D formatting',       group: 'reason',  duration: 2000 },
  { id: 'intel',       label: 'Scenario + pattern match',    group: 'intel',   duration: 3500 },
];

const GROUP_LABELS = {
  fetch: 'Parallel Fetch',
  process: 'Pre-Synthesis',
  reason: '6-Call Reasoning Chain',
  intel: 'Intelligence Layer',
};

const GROUP_COLORS = {
  fetch: 'text-trm-info',
  process: 'text-trm-warn',
  reason: 'text-accent',
  intel: 'text-trm-pos',
};

export default function PipelineVisualizer({ ticker, fastForward = false, onComplete }) {
  const [completedIds, setCompletedIds] = useState(new Set());
  const [activeId, setActiveId] = useState(null);
  const [progress, setProgress] = useState(0);
  const progressRef = useRef(null);
  const fastForwardRef = useRef(fastForward);

  useEffect(() => {
    fastForwardRef.current = fastForward;
  }, [fastForward]);

  // Animate global progress bar with GSAP
  useEffect(() => {
    if (!progressRef.current) return;
    gsap.to(progressRef.current, {
      scaleX: progress / 100,
      duration: 0.6,
      ease: 'power2.out',
    });
  }, [progress]);

  // Step through pipeline with a high-frequency tick engine
  useEffect(() => {
    let idx = 0;
    let elapsed = 0;
    
    const interval = setInterval(() => {
      if (idx >= PIPELINE_STEPS.length) {
        clearInterval(interval);
        setProgress(100);
        setTimeout(() => onComplete(), 600);
        return;
      }

      const step = PIPELINE_STEPS[idx];
      setActiveId(step.id);
      
      const targetDuration = fastForwardRef.current ? 1500 : step.duration;
      elapsed += 50;
      
      if (elapsed >= targetDuration) {
        setCompletedIds(prev => new Set([...prev, step.id]));
        setProgress(Math.round(((idx + 1) / PIPELINE_STEPS.length) * 100));
        idx++;
        elapsed = 0;
      } else {
        // Smooth progress interpolation
        const currentProgress = ((idx + Math.min(1, elapsed/targetDuration)) / PIPELINE_STEPS.length) * 100;
        setProgress(Math.round(currentProgress));
      }
    }, 50);

    return () => clearInterval(interval);
  }, [onComplete]);

  // Build visible steps: only active + next 2 (completed ones slide out)
  const allSteps = PIPELINE_STEPS;
  const activeIndex = allSteps.findIndex(s => s.id === activeId);

  // Show: the active step and the next 2 upcoming steps
  const visibleSteps = allSteps.slice(
    Math.max(0, activeIndex),
    Math.min(allSteps.length, activeIndex + 3)
  );

  // Determine current group label
  const activeStep = allSteps[activeIndex];
  const currentGroupLabel = activeStep ? GROUP_LABELS[activeStep.group] : '';
  const currentGroupColor = activeStep ? GROUP_COLORS[activeStep.group] : '';

  return (
    <div className="w-full max-w-xl mx-auto flex flex-col items-center justify-center min-h-[65dvh] py-16">

      {/* ── Pinned header: ticker + progress bar ── */}
      <div className="w-full mb-12">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-8"
        >
          <span className="inline-block px-3 py-1 rounded-md border border-border-primary bg-bg-secondary font-mono text-[11px] text-text-muted tracking-wider mb-4">
            {ticker}
          </span>
          <h2 className="text-xl font-medium tracking-tight text-text-primary">
            Synthesizing intelligence brief
          </h2>
        </motion.div>

        {/* Progress bar — always visible */}
        <div className="w-full max-w-md mx-auto">
          <div className="h-[2px] w-full bg-border-primary rounded-full overflow-hidden">
            <div
              ref={progressRef}
              className="h-full bg-accent origin-left rounded-full"
              style={{ transform: 'scaleX(0)' }}
            />
          </div>
          <div className="flex justify-between mt-2">
            <span className="text-[10px] font-mono text-text-muted tabular-nums">{progress}%</span>
            <span className="text-[10px] font-mono text-text-muted tabular-nums">
              {completedIds.size}/{PIPELINE_STEPS.length}
            </span>
          </div>
        </div>
      </div>

      {/* ── Current group label ── */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentGroupLabel}
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 6 }}
          transition={{ duration: 0.3 }}
          className="flex items-center gap-3 w-full mb-5"
        >
          <span className={`text-[10px] font-mono uppercase tracking-widest ${currentGroupColor}`}>
            {currentGroupLabel}
          </span>
          <div className="h-px flex-1 bg-border-subtle" />
        </motion.div>
      </AnimatePresence>

      {/* ── Steps: completed slide up, active + next visible ── */}
      <div className="w-full relative" style={{ minHeight: '140px' }}>
        <AnimatePresence mode="popLayout">
          {visibleSteps.map((step) => {
            const isDone = completedIds.has(step.id);
            const isActive = step.id === activeId;

            return (
              <motion.div
                key={step.id}
                layout
                initial={{ opacity: 0, y: 24 }}
                animate={{
                  opacity: isActive ? 1 : 0.35,
                  y: 0,
                }}
                exit={{ opacity: 0, y: -32, filter: 'blur(3px)' }}
                transition={{
                  layout: { type: 'spring', stiffness: 200, damping: 28 },
                  opacity: { duration: 0.3 },
                  y: { duration: 0.35 },
                  filter: { duration: 0.25 },
                }}
                className={`flex items-center gap-4 px-4 py-3 rounded-lg border mb-2 transition-colors duration-300
                  ${isActive
                    ? 'border-accent-border bg-accent-dim'
                    : 'border-transparent bg-transparent'
                  }`}
              >
                {/* Status indicator */}
                <div className="relative w-4 h-4 flex items-center justify-center shrink-0">
                  {isDone && (
                    <motion.svg
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                      width="14" height="14" viewBox="0 0 14 14"
                    >
                      <circle cx="7" cy="7" r="6" fill="none" stroke="var(--color-accent)" strokeWidth="1.5" />
                      <motion.path
                        d="M4 7.2 L6 9.2 L10 5"
                        fill="none" stroke="var(--color-accent)" strokeWidth="1.5"
                        strokeLinecap="round" strokeLinejoin="round"
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: 1 }}
                        transition={{ duration: 0.3, delay: 0.1 }}
                      />
                    </motion.svg>
                  )}
                  {isActive && (
                    <div className="relative">
                      <div className="w-2 h-2 rounded-full bg-accent" />
                      <div className="absolute inset-0 w-2 h-2 rounded-full bg-accent animate-ping opacity-60" />
                    </div>
                  )}
                  {!isDone && !isActive && (
                    <div className="w-1.5 h-1.5 rounded-full bg-border-hover" />
                  )}
                </div>

                {/* Label */}
                <span className={`font-mono text-[13px] transition-colors duration-300
                  ${isActive ? 'text-text-primary' : 'text-text-muted/50'}
                `}>
                  {step.label}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* ── Completed steps counter ── */}
      {completedIds.size > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-6 flex items-center gap-2"
        >
          <div className="flex -space-x-1">
            {Array.from({ length: Math.min(completedIds.size, 6) }).map((_, i) => (
              <div key={i} className="w-2 h-2 rounded-full bg-accent border border-bg-primary" />
            ))}
            {completedIds.size > 6 && (
              <span className="text-[10px] font-mono text-text-muted ml-2">+{completedIds.size - 6}</span>
            )}
          </div>
          <span className="text-[10px] font-mono text-text-muted">
            {completedIds.size} completed
          </span>
        </motion.div>
      )}
    </div>
  );
}
