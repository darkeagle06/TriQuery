import React, { useEffect, useState } from 'react'
import type { ExplainPlanStep, ExplainResponse, PresetItem, UnifiedQuery } from '../types/api'
import { apiClient } from '../services/api'
import { Badge } from '../components/common/Badge'
import { ErrorState } from '../components/common/ErrorState'

interface ExplainViewProps {
  initialQuery?: UnifiedQuery | null
}

export const ExplainView: React.FC<ExplainViewProps> = ({ initialQuery }) => {
  const [presets, setPresets] = useState<PresetItem[]>([])
  const [selectedPresetId, setSelectedPresetId] = useState<string>('5')
  const [activeQuery, setActiveQuery] = useState<UnifiedQuery | null>(initialQuery || null)

  const [explainData, setExplainData] = useState<ExplainResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // 1. Fetch presets on mount if no initial query provided
  useEffect(() => {
    let isMounted = true
    const init = async () => {
      try {
        const res = await apiClient.getPresets()
        if (isMounted) {
          setPresets(res.presets)
          if (!activeQuery) {
            const p5 = res.presets.find((p) => p.preset_id === '5') || res.presets[0]
            if (p5) {
              setSelectedPresetId(p5.preset_id)
              setActiveQuery(p5.query)
            }
          }
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to fetch presets.')
      }
    }
    init()
    return () => {
      isMounted = false
    }
  }, [])

  // 2. Fetch explanation whenever activeQuery changes
  const fetchExplain = async (query: UnifiedQuery) => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.explainUnifiedQuery(query)
      setExplainData(res)
    } catch (err: any) {
      setError(err.message || 'Failed to explain query on backend.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (activeQuery) {
      fetchExplain(activeQuery)
    }
  }, [activeQuery])

  const handleSelectPreset = (p: PresetItem) => {
    setSelectedPresetId(p.preset_id)
    setActiveQuery(p.query)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem', paddingBottom: '4rem' }}>
      {/* View Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
          <Badge variant="amber" size="sm">EXPLAINABILITY & VIVA ENGINE</Badge>
          <span className="mono text-muted" style={{ fontSize: 'var(--text-xs)' }}>
            POST /api/query/explain
          </span>
        </div>
        <h1 style={{ fontSize: 'var(--text-3xl)' }}>Execution Plan & Algorithmic Explainability</h1>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
          Transparent query planning, step dependencies, algorithmic time/space complexities, and consensus ranking justifications.
        </p>
      </div>

      {/* Preset Selector */}
      {presets.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span className="mono text-muted" style={{ fontSize: '11px' }}>Inspect Benchmark:</span>
          {presets.map((p) => (
            <button
              key={p.preset_id}
              onClick={() => handleSelectPreset(p)}
              className="mono"
              style={{
                fontSize: '11px',
                padding: '0.3rem 0.65rem',
                borderRadius: 'var(--radius-xs)',
                background: selectedPresetId === p.preset_id ? 'var(--accent-cyan-dim)' : 'rgba(255, 255, 255, 0.04)',
                border: `1px solid ${selectedPresetId === p.preset_id ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`,
                color: selectedPresetId === p.preset_id ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                cursor: 'pointer',
              }}
            >
              Preset #{p.preset_id} ({p.target_paradigms.join(' + ')})
            </button>
          ))}
        </div>
      )}

      {/* Loading or Error */}
      {loading && (
        <div className="tech-panel mono text-muted" style={{ padding: '2.5rem', textAlign: 'center' }}>
          Deconstructing execution plan and computing algorithmic complexity...
        </div>
      )}

      {error && <ErrorState message={error} onRetry={() => activeQuery && fetchExplain(activeQuery)} isRetrying={loading} />}

      {/* Explanation Report */}
      {explainData && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {/* Query Summary & Paradigms Banner */}
          <section
            className="tech-panel"
            style={{
              padding: '1.4rem',
              background: 'var(--bg-surface-elevated)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.8rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <span className="mono text-cyan" style={{ fontSize: 'var(--text-sm)', fontWeight: 600 }}>
                  QUERY: {explainData.query_name || explainData.query_id}
                </span>
                <Badge variant="cyan" size="sm">
                  {explainData.fusion_strategy.toUpperCase()}
                </Badge>
              </div>

              <div style={{ display: 'flex', gap: '0.4rem' }}>
                {explainData.target_paradigms.map((p) => (
                  <Badge
                    key={p}
                    size="sm"
                    variant={p === 'relational' ? 'cyan' : p === 'graph' ? 'purple' : 'emerald'}
                  >
                    {p.toUpperCase()}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Complexity Badges */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
                gap: '1rem',
                paddingTop: '0.8rem',
                borderTop: '1px solid var(--border-subtle)',
              }}
            >
              <div className="mono" style={{ fontSize: '11.5px' }}>
                <span className="text-muted">Time Complexity (Theoretical Upper Bound): </span>
                <span className="text-cyan" style={{ fontWeight: 600 }}>{explainData.time_complexity}</span>
              </div>
              <div className="mono" style={{ fontSize: '11.5px' }}>
                <span className="text-muted">Space Complexity (Theoretical Peak Working Set): </span>
                <span className="text-indigo" style={{ fontWeight: 600 }}>{explainData.space_complexity}</span>
              </div>
              <div className="mono" style={{ fontSize: '11.5px' }}>
                <span className="text-muted">RRF Smoothing Constant: </span>
                <span className="text-amber" style={{ fontWeight: 600 }}>k = {explainData.rrf_evidence.k_constant}</span>
              </div>
            </div>
            <div className="mono text-dim" style={{ fontSize: '10px', marginTop: '0.2rem' }}>
              * Big-O metrics reflect theoretical algorithmic worst-case bounds; inspect live wall-clock measurements in Query Studio telemetry.
            </div>
          </section>

          {/* Step-by-Step Execution Plan */}
          <section style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h3 style={{ fontSize: 'var(--text-xl)' }}>Planned Pipeline Steps ({explainData.plan_steps.length})</h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {explainData.plan_steps.map((step: ExplainPlanStep) => (
                <div
                  key={step.step}
                  className="tech-panel"
                  style={{
                    padding: '1.2rem',
                    background: 'var(--bg-surface)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem',
                    borderLeft: `3px solid ${
                      step.engine === 'relational'
                        ? 'var(--engine-relational)'
                        : step.engine === 'graph'
                          ? 'var(--engine-graph)'
                          : step.engine === 'vector'
                            ? 'var(--engine-vector)'
                            : 'var(--engine-fusion)'
                    }`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <span className="mono text-cyan" style={{ fontSize: 'var(--text-sm)', fontWeight: 700 }}>
                        STEP #{step.step}
                      </span>
                      <Badge
                        size="sm"
                        variant={
                          step.engine === 'relational'
                            ? 'cyan'
                            : step.engine === 'graph'
                              ? 'purple'
                              : step.engine === 'vector'
                                ? 'emerald'
                                : 'amber'
                        }
                      >
                        {step.engine.toUpperCase()}
                      </Badge>
                      <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {step.action}
                      </span>
                    </div>

                    <span className="mono text-muted" style={{ fontSize: '11px' }}>
                      Complexity: {step.complexity}
                    </span>
                  </div>

                  {step.depends_on && step.depends_on.length > 0 && (
                    <div className="mono text-dim" style={{ fontSize: '11px' }}>
                      Depends on step(s): {step.depends_on.join(', ')}
                    </div>
                  )}

                  {Object.keys(step.filters_or_args).length > 0 && (
                    <div
                      className="mono"
                      style={{
                        padding: '0.5rem 0.8rem',
                        background: 'rgba(0, 0, 0, 0.3)',
                        borderRadius: 'var(--radius-xs)',
                        fontSize: '11px',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      Arguments: {JSON.stringify(step.filters_or_args)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Viva Justifications & Architectural Defense */}
          <section
            className="tech-panel tech-corner-marks"
            style={{
              padding: '1.6rem',
              background: 'var(--bg-surface-elevated)',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.2rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Badge variant="amber" size="sm">VIVA DEFENSE JUSTIFICATIONS</Badge>
              <span className="mono text-muted" style={{ fontSize: 'var(--text-xs)' }}>
                Academic & Architectural Defense Arguments
              </span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))',
                gap: '1.2rem',
              }}
            >
              {Object.entries(explainData.viva_justifications).map(([key, text]) => (
                <div
                  key={key}
                  style={{
                    padding: '1rem',
                    background: 'var(--bg-void)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.4rem',
                  }}
                >
                  <span
                    className="mono text-amber"
                    style={{
                      fontSize: 'var(--text-xs)',
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                    }}
                  >
                    {key.replace(/_/g, ' ')}
                  </span>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.55 }}>
                    {text}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
