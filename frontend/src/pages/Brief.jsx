import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'motion/react';
import PipelineVisualizer from '../components/PipelineVisualizer';
import ConfidenceRing from '../components/ConfidenceRing';

/* ── Stagger animation helper ── */
const stagger = (i, base = 0.08) => ({ delay: i * base });

export default function Brief() {
  const { ticker } = useParams();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isDataReady, setIsDataReady] = useState(false);
  const [isAnimationDone, setIsAnimationDone] = useState(false);

  // Called when PipelineVisualizer hits 100%
  const handlePipelineComplete = useCallback(() => {
    setIsAnimationDone(true);
  }, []);

  const fetchInitiated = useRef(null);

  // When both the fetch is resolved AND the animation is finished, reveal data
  useEffect(() => {
    if (isDataReady && isAnimationDone) {
      setLoading(false);
    }
  }, [isDataReady, isAnimationDone]);

  useEffect(() => {
    if (fetchInitiated.current === ticker) return;
    fetchInitiated.current = ticker;

    const fetchBrief = async () => {
      try {
        setLoading(true);
        // Using use_cache=true as it was requested to hit live/cached backend
        const response = await fetch(`/brief/${ticker.toUpperCase()}?use_cache=true`, {
          method: 'POST',
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch brief');
        }
        
        const json = await response.json();
        setData(json);
        setIsDataReady(true);
      } catch (err) {
        console.error('Fetch error:', err);
        setError(err.message);
        setIsDataReady(true); // Ensures it doesn't spin forever
      }
    };

    fetchBrief();
  }, [ticker]);

  const scenarioColor = {
    bull: 'var(--color-trm-pos)',
    base: 'var(--color-trm-warn)',
    bear: 'var(--color-trm-neg)',
  };

  // Helper to safely access triggers which might be missing in the JSON
  const getTriggers = (scenario) => {
    if (scenario?.triggers) return scenario.triggers;
    if (scenario?.drivers) return scenario.drivers; // Fallback to drivers
    if (scenario?.risks) return scenario.risks; // Fallback to risks
    return [];
  };

  if (error) {
    return (
      <div className="min-h-[100dvh] bg-bg-primary flex items-center justify-center p-8">
        <div className="text-center">
          <p className="text-trm-neg font-mono mb-4">Error: {error}</p>
          <Link to="/" className="text-accent hover:underline font-mono">← Back Home</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[100dvh] bg-bg-primary">
      {/* ── Header ── */}
      <header className="sticky top-0 z-50 border-b border-border-primary bg-bg-primary/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 md:px-12 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="w-8 h-8 flex items-center justify-center rounded-md border border-border-primary text-text-muted hover:text-text-primary hover:border-border-hover active:translate-y-px transition-all"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M8.5 3L4.5 7L8.5 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </Link>
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm font-medium tracking-wider text-text-primary">{ticker.toUpperCase()}</span>
              {!loading && data?.data_quality?.status && (
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                  data.data_quality.status === 'healthy' 
                    ? 'text-accent bg-accent-dim border-accent-border'
                    : 'text-trm-warn bg-trm-warn/10 border-trm-warn/20'
                }`}>
                  {data.data_quality.status.toUpperCase()}
                </span>
              )}
            </div>
          </div>
          {!loading && data && (
            <div className="hidden md:flex items-center gap-4 text-[10px] font-mono text-text-muted tabular-nums">
              <span>{data.sources?.length || 0} sources</span>
              <span className="w-1 h-1 rounded-full bg-border-hover" />
              <span>{data.contradictions_resolved?.length || 0} contradictions resolved</span>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 md:px-12 py-10">
        {loading || !data ? (
          <PipelineVisualizer 
            ticker={ticker} 
            fastForward={isDataReady} 
            onComplete={handlePipelineComplete} 
          />
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col gap-16 pb-32"
          >
            {/* ═══ Section 1: Verdict ═══ */}
            <section>
              <motion.div {...stagger(0)} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-[10px] font-mono text-text-muted uppercase tracking-widest">Executive Verdict</span>
                  <div className="h-px flex-1 bg-border-subtle" />
                </div>
              </motion.div>

              <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
                {/* Verdict text */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.1 }}
                  className="md:col-span-8"
                >
                  <p className="text-xl md:text-2xl font-light leading-relaxed text-text-primary max-w-[58ch] mb-8">
                    {data.verdict?.tldr || "Verdict TL;DR unavailable"}
                  </p>
                  <div className="flex flex-wrap items-center gap-3">
                    {[
                      { label: 'Scenario', value: data.verdict?.recommended_scenario, accent: true },
                      { label: 'Confidence', value: data.verdict?.confidence_level },
                      { label: 'Priority', value: data.verdict?.watchlist_priority },
                    ].map(tag => tag.value && (
                      <div key={tag.label} className={`px-3 py-1.5 rounded-md border font-mono text-[11px] uppercase tracking-wider
                        ${tag.accent
                          ? 'border-accent-border bg-accent-dim text-accent'
                          : 'border-border-primary bg-bg-secondary text-text-secondary'}
                      `}>
                        <span className="text-text-muted mr-2">{tag.label}</span>
                        {tag.value}
                      </div>
                    ))}
                  </div>
                </motion.div>

                {/* Confidence rings */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.25 }}
                  className="md:col-span-4 flex items-center justify-center md:justify-end gap-6"
                >
                  {data.scenarios && Object.entries(data.scenarios).map(([key, scenario]) => (
                    <ConfidenceRing
                      key={key}
                      value={scenario.confidence || 0}
                      size={68}
                      color={scenarioColor[key]}
                      label={key}
                    />
                  ))}
                </motion.div>
              </div>
            </section>

            {/* ═══ Section 2: Scenarios — asymmetric layout ═══ */}
            {data.scenarios && (
              <section>
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.15 }}>
                  <div className="flex items-center gap-3 mb-6">
                    <span className="text-[10px] font-mono text-text-muted uppercase tracking-widest">Scenario Analysis</span>
                    <div className="h-px flex-1 bg-border-subtle" />
                  </div>
                </motion.div>

                <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                  {Object.entries(data.scenarios).map(([key, scenario], i) => {
                    const color = scenarioColor[key];
                    // Bull gets 5 cols, Base 3 cols, Bear 4 cols for asymmetry
                    const colSpan = i === 0 ? 'md:col-span-5' : i === 1 ? 'md:col-span-3' : 'md:col-span-4';
                    const triggers = getTriggers(scenario);

                    return (
                      <motion.div
                        key={key}
                        initial={{ opacity: 0, y: 24 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.2 + i * 0.1 }}
                        className={`${colSpan} bg-bg-secondary border border-border-primary rounded-xl p-6 inner-light group hover:border-border-hover transition-colors duration-300 flex flex-col`}
                      >
                        {/* Scenario header */}
                        <div className="flex items-center justify-between mb-5">
                          <div className="flex items-center gap-2.5">
                            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                            <h3 className="text-sm font-medium capitalize" style={{ color }}>{key} Case</h3>
                          </div>
                          <span className="font-mono text-lg tabular-nums text-text-primary">
                            {Math.round((scenario.confidence || 0) * 100)}%
                          </span>
                        </div>

                        {/* Summary */}
                        <p className="text-[13px] text-text-secondary leading-relaxed mb-6 flex-1">
                          {scenario.summary || "No summary available."}
                        </p>

                        {/* Triggers */}
                        {triggers && triggers.length > 0 && (
                          <div className="space-y-3 mb-5">
                            <span className="text-[10px] font-mono text-text-muted uppercase tracking-widest block">Triggers</span>
                            {triggers.map((t, j) => (
                              <div key={j} className="text-[12px] font-mono text-text-primary bg-bg-primary px-3 py-2 rounded-md border border-border-subtle">
                                {t}
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Expected move */}
                        {scenario.expected_move && (
                          <div className="mt-auto pt-2">
                            <span className="text-[10px] font-mono text-text-muted uppercase tracking-widest block mb-2">Expected Move</span>
                            <div className="font-mono text-sm px-3 py-2 rounded-md border" style={{
                              color,
                              backgroundColor: `color-mix(in oklch, ${color} 8%, transparent)`,
                              borderColor: `color-mix(in oklch, ${color} 15%, transparent)`,
                            }}>
                              {scenario.expected_move.range_low} to {scenario.expected_move.range_high}
                            </div>
                          </div>
                        )}
                      </motion.div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* ═══ Section 3: Historical Pattern Match ═══ */}
            {data.historical_matches && data.historical_matches.length > 0 && (
              <section>
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.2 }}>
                  <div className="flex items-center gap-3 mb-6">
                    <span className="text-[10px] font-mono text-text-muted uppercase tracking-widest">Historical Pattern Match</span>
                    <div className="h-px flex-1 bg-border-subtle" />
                  </div>
                </motion.div>

                <div className="space-y-4">
                  {data.historical_matches.map((match, i) => {
                    const isPositive = match.return_5d?.startsWith('+');
                    return (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.25 + i * 0.1 }}
                        className="bg-bg-secondary border border-border-primary rounded-xl p-6 inner-light hover:border-border-hover transition-colors duration-300"
                      >
                        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
                          {/* Quarter + similarity */}
                          <div className="md:col-span-3">
                            <span className="font-mono text-lg text-text-primary block">{match.quarter}</span>
                            <span className="text-[11px] font-mono text-trm-info tabular-nums">
                              {Math.round((match.similarity_score || 0) * 100)}% similar
                            </span>
                          </div>

                          {/* Outcome & Factors */}
                          <div className="md:col-span-7 space-y-4">
                            <p className="text-[14px] text-text-primary leading-relaxed">{match.outcome || match.setup_summary}</p>
                            
                            {match.key_similarity_factors && match.key_similarity_factors.length > 0 && (
                              <div className="space-y-2 pt-1">
                                {match.key_similarity_factors.map((f, j) => (
                                  <div key={j} className="flex items-start gap-2.5">
                                    <div className="mt-2 w-1.5 h-1.5 rounded-full bg-border-hover flex-shrink-0" />
                                    <span className="text-[13px] text-text-secondary leading-relaxed">{f}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* 5-day return */}
                          <div className="md:col-span-2 text-right">
                            <span className={`font-mono text-xl tabular-nums font-medium ${isPositive ? 'text-trm-pos' : 'text-trm-neg'}`}>
                              {match.return_5d || "N/A"}
                            </span>
                            <span className="block text-[10px] font-mono text-text-muted mt-0.5">5-day return</span>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* ═══ Section 4: Data Quality Footer ═══ */}
            {data.data_quality && (
              <motion.section
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4, duration: 0.5 }}
              >
                <div className="flex items-center gap-3 mb-6">
                  <span className="text-[10px] font-mono text-text-muted uppercase tracking-widest">Data Provenance</span>
                  <div className="h-px flex-1 bg-border-subtle" />
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: 'Web Chunks', value: data.data_quality.web_chunks_fetched || 0 },
                    { label: 'yFinance', value: data.data_quality.yfinance_chunks || 0 },
                    { label: 'SEC Filing', value: data.data_quality.sec_chunks || 0 },
                    { label: 'Contradictions', value: data.contradictions_resolved?.length || 0 },
                  ].map((metric, i) => (
                    <div key={i} className="bg-bg-secondary border border-border-primary rounded-lg p-4 inner-light">
                      <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider block mb-1">{metric.label}</span>
                      <span className="font-mono text-2xl text-text-primary tabular-nums">{metric.value}</span>
                    </div>
                  ))}
                </div>
              </motion.section>
            )}

          </motion.div>
        )}
      </main>
    </div>
  );
}
