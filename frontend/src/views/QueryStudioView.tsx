import React, { useEffect, useState } from 'react'
import type { FusedItem, PresetItem, UnifiedExecutionResult, UnifiedQuery } from '../types/api'
import { apiClient } from '../services/api'
import { Badge } from '../components/common/Badge'
import { Button } from '../components/common/Button'
import { ErrorState } from '../components/common/ErrorState'
import type { NavigationDestination } from '../components/layout/Header'

interface QueryStudioViewProps {
  onNavigate: (dest: NavigationDestination) => void
  onSelectQueryForExplain: (query: UnifiedQuery) => void
}

interface ExecutionHistoryItem {
  id: string
  queryName: string
  presetId?: string
  totalLatencyMs: number
  fusedCount: number
  timestamp: string
}

export const QueryStudioView: React.FC<QueryStudioViewProps> = ({
  onNavigate,
  onSelectQueryForExplain,
}) => {
  const [presets, setPresets] = useState<PresetItem[]>([])
  const [selectedPresetId, setSelectedPresetId] = useState<string>('5')
  const [activeQuery, setActiveQuery] = useState<UnifiedQuery | null>(null)

  const [loadingPresets, setLoadingPresets] = useState<boolean>(true)
  const [executing, setExecuting] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [executionResult, setExecutionResult] = useState<UnifiedExecutionResult | null>(null)

  // Expanded card for inspecting deep metadata
  const [expandedEntityId, setExpandedEntityId] = useState<string | null>(null)

  // Session-observed execution history
  const [executionHistory, setExecutionHistory] = useState<ExecutionHistoryItem[]>([])

  // 1. Fetch presets on mount
  useEffect(() => {
    let isMounted = true
    const loadPresets = async () => {
      setLoadingPresets(true)
      setError(null)
      try {
        const res = await apiClient.getPresets()
        if (isMounted) {
          setPresets(res.presets)
          // Default to preset 5 (3-Engine Unified Benchmark)
          const p5 = res.presets.find((p) => p.preset_id === '5') || res.presets[0]
          if (p5) {
            setSelectedPresetId(p5.preset_id)
            setActiveQuery(p5.query)
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to fetch benchmark presets from API.')
        }
      } finally {
        if (isMounted) setLoadingPresets(false)
      }
    }
    loadPresets()
    return () => {
      isMounted = false
    }
  }, [])

  // 2. Switch preset
  const handleSelectPreset = (preset: PresetItem) => {
    setSelectedPresetId(preset.preset_id)
    setActiveQuery(preset.query)
    setExecutionResult(null)
    setError(null)
    setExpandedEntityId(null)
  }

  // 3. Execute query
  const handleExecute = async () => {
    if (!activeQuery) return
    setExecuting(true)
    setError(null)
    setExpandedEntityId(null)
    try {
      const res = await apiClient.executeUnifiedQuery(activeQuery)
      setExecutionResult(res)

      // Record in session execution history
      const now = new Date()
      const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      setExecutionHistory((prev) => [
        {
          id: `${Date.now()}`,
          queryName: activeQuery.name || activeQuery.query_id,
          presetId: selectedPresetId,
          totalLatencyMs: res.total_latency_ms,
          fusedCount: res.fused_results.length,
          timestamp: timeStr,
        },
        ...prev.slice(0, 9),
      ])
    } catch (err: any) {
      setError(err.message || 'Query execution failed on backend.')
    } finally {
      setExecuting(false)
    }
  }

  // Active paradigm checks
  const hasRelational = !!activeQuery?.relational
  const hasGraph = !!activeQuery?.graph
  const hasVector = !!activeQuery?.vector

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2.2rem', paddingBottom: '4rem' }}>
      {/* Studio Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
          <Badge variant="cyan" size="sm">ENGINE WORKBENCH</Badge>
          <span className="mono text-muted" style={{ fontSize: 'var(--text-xs)' }}>
            POST /api/query/unified
          </span>
        </div>
        <h1 style={{ fontSize: 'var(--text-3xl)' }}>Multi-Paradigm Query Studio</h1>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
          Execute and inspect cross-paradigm queries with automatic plan optimization and Reciprocal Rank Fusion.
        </p>
      </div>

      {/* Preset Benchmarks Selector */}
      <section className="tech-panel" style={{ padding: '1.2rem', background: 'var(--bg-surface-elevated)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.8rem' }}>
          <span className="mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            CANONICAL BENCHMARK PRESETS
          </span>
          <span className="mono text-muted" style={{ fontSize: '11px' }}>
            {presets.length} presets loaded
          </span>
        </div>

        {loadingPresets ? (
          <div className="mono text-muted" style={{ fontSize: 'var(--text-xs)', padding: '0.8rem 0' }}>
            Loading canonical benchmark queries from backend...
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
              gap: '0.75rem',
            }}
          >
            {presets.map((p) => {
              const isSelected = selectedPresetId === p.preset_id
              return (
                <button
                  key={p.preset_id}
                  onClick={() => handleSelectPreset(p)}
                  className="tech-panel"
                  style={{
                    padding: '0.8rem 1rem',
                    textAlign: 'left',
                    background: isSelected ? 'rgba(56, 189, 248, 0.08)' : 'var(--bg-surface)',
                    border: `1px solid ${isSelected ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`,
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.4rem',
                    cursor: 'pointer',
                    transition: 'var(--transition-fast)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span className="mono text-cyan" style={{ fontSize: 'var(--text-xs)', fontWeight: 600 }}>
                      Preset #{p.preset_id}
                    </span>
                    <div style={{ display: 'flex', gap: '0.2rem' }}>
                      {p.target_paradigms.map((paradigm) => (
                        <Badge
                          key={paradigm}
                          size="sm"
                          variant={
                            paradigm === 'relational'
                              ? 'cyan'
                              : paradigm === 'graph'
                                ? 'purple'
                                : 'emerald'
                          }
                        >
                          {paradigm[0].toUpperCase()}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <span
                    style={{
                      fontSize: 'var(--text-sm)',
                      fontWeight: 600,
                      color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                      lineHeight: 1.25,
                    }}
                  >
                    {p.name.replace(/_/g, ' ')}
                  </span>

                  <span
                    style={{
                      fontSize: '11px',
                      color: 'var(--text-dim)',
                      lineHeight: 1.35,
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    {p.description}
                  </span>
                </button>
              )
            })}
          </div>
        )}
      </section>

      {/* Query Configuration & Action Bar */}
      {activeQuery && (
        <section
          className="tech-panel"
          style={{
            padding: '1.4rem',
            background: 'var(--bg-surface)',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.2rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <h3 style={{ fontSize: 'var(--text-base)', color: 'var(--text-primary)' }}>
                  Active Query: {activeQuery.name || activeQuery.query_id}
                </h3>
                <Badge variant="amber" size="sm">
                  {activeQuery.fusion?.strategy?.toUpperCase() || 'RRF'} (k={activeQuery.fusion?.k_constant || 60})
                </Badge>

                {/* Visual paradigm invocation indicators */}
                <div style={{ display: 'flex', gap: '0.25rem' }}>
                  <Badge variant={hasRelational ? 'cyan' : 'muted'} size="sm">
                    SQL {hasRelational ? '●' : '○'}
                  </Badge>
                  <Badge variant={hasGraph ? 'purple' : 'muted'} size="sm">
                    GRAPH {hasGraph ? '●' : '○'}
                  </Badge>
                  <Badge variant={hasVector ? 'emerald' : 'muted'} size="sm">
                    VECTOR {hasVector ? '●' : '○'}
                  </Badge>
                </div>
              </div>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: 0 }}>
                {activeQuery.description}
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
              <Button
                variant="primary"
                onClick={handleExecute}
                loading={executing}
                icon={<span className="mono">⚡</span>}
              >
                Execute Unified Query
              </Button>

              <Button
                variant="secondary"
                onClick={() => {
                  onSelectQueryForExplain(activeQuery)
                  onNavigate('explain')
                }}
              >
                Inspect Plan
              </Button>
            </div>
          </div>

          {/* Subqueries Definition Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))',
              gap: '1rem',
            }}
          >
            {/* Relational subquery */}
            <div
              className="tech-panel"
              style={{
                padding: '0.9rem',
                borderLeft: `3px solid ${hasRelational ? 'var(--engine-relational)' : 'var(--border-subtle)'}`,
                background: 'var(--bg-surface-elevated)',
                opacity: hasRelational ? 1 : 0.6,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span className="mono text-cyan" style={{ fontSize: 'var(--text-xs)', fontWeight: 600 }}>
                  RELATIONAL SUBQUERY
                </span>
                <Badge variant={hasRelational ? 'cyan' : 'muted'} size="sm">
                  {hasRelational ? 'ACTIVE' : 'BYPASSED'}
                </Badge>
              </div>
              {activeQuery.relational ? (
                <div className="mono" style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  {activeQuery.relational.track && <div>Track: <span className="text-cyan">{activeQuery.relational.track}</span></div>}
                  {activeQuery.relational.college_id && <div>College ID: {activeQuery.relational.college_id}</div>}
                  {activeQuery.relational.min_cash_prize && <div>Min Cash Prize: ₹{activeQuery.relational.min_cash_prize}</div>}
                </div>
              ) : (
                <span className="mono text-dim" style={{ fontSize: '11px' }}>No relational filter applied</span>
              )}
            </div>

            {/* Graph subquery */}
            <div
              className="tech-panel"
              style={{
                padding: '0.9rem',
                borderLeft: `3px solid ${hasGraph ? 'var(--engine-graph)' : 'var(--border-subtle)'}`,
                background: 'var(--bg-surface-elevated)',
                opacity: hasGraph ? 1 : 0.6,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span className="mono text-purple" style={{ fontSize: 'var(--text-xs)', fontWeight: 600 }}>
                  GRAPH SUBQUERY
                </span>
                <Badge variant={hasGraph ? 'purple' : 'muted'} size="sm">
                  {hasGraph ? 'ACTIVE' : 'BYPASSED'}
                </Badge>
              </div>
              {activeQuery.graph ? (
                <div className="mono" style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  {activeQuery.graph.start_node && <div>Start Node: <span className="text-indigo">{activeQuery.graph.start_node}</span></div>}
                  {activeQuery.graph.target_type && <div>Target Type: {activeQuery.graph.target_type}</div>}
                  {activeQuery.graph.max_depth && <div>Max Depth: {activeQuery.graph.max_depth} hops</div>}
                </div>
              ) : (
                <span className="mono text-dim" style={{ fontSize: '11px' }}>No graph traversal applied</span>
              )}
            </div>

            {/* Vector subquery */}
            <div
              className="tech-panel"
              style={{
                padding: '0.9rem',
                borderLeft: `3px solid ${hasVector ? 'var(--engine-vector)' : 'var(--border-subtle)'}`,
                background: 'var(--bg-surface-elevated)',
                opacity: hasVector ? 1 : 0.6,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span className="mono text-emerald" style={{ fontSize: 'var(--text-xs)', fontWeight: 600 }}>
                  VECTOR SUBQUERY
                </span>
                <Badge variant={hasVector ? 'emerald' : 'muted'} size="sm">
                  {hasVector ? 'ACTIVE' : 'BYPASSED'}
                </Badge>
              </div>
              {activeQuery.vector ? (
                <div className="mono" style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  <div>Query: <span className="text-emerald">"{activeQuery.vector.query_text}"</span></div>
                  <div>Top-K: {activeQuery.vector.top_k || 5} candidates</div>
                </div>
              ) : (
                <span className="mono text-dim" style={{ fontSize: '11px' }}>No vector similarity applied</span>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Error Display */}
      {error && (
        <ErrorState
          title="Query Execution Error"
          message={error}
          onRetry={handleExecute}
          isRetrying={executing}
        />
      )}

      {/* Execution Results Section */}
      {executionResult && (
        <section style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Telemetry Waterfall Card */}
          <div
            className="tech-panel tech-corner-marks"
            style={{
              padding: '1.4rem',
              background: 'var(--bg-surface-elevated)',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <span className="mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                  LIVE MEASURED TELEMETRY (WALL-CLOCK):
                </span>
                <span className="mono" style={{ fontSize: 'var(--text-base)', color: 'var(--accent-cyan)', fontWeight: 700 }}>
                  {executionResult.total_latency_ms.toFixed(3)} ms total
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Badge variant="healthy" size="sm" dot>
                  {executionResult.fused_results.length} fused records returned
                </Badge>
              </div>
            </div>

            {/* Stage Latency Comparative Breakdown */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))',
                gap: '0.6rem',
              }}
            >
              {Object.entries(executionResult.stage_latencies_ms).map(([stage, lat]) => {
                const percentage = executionResult.total_latency_ms > 0
                  ? Math.min(100, Math.max(5, (lat / executionResult.total_latency_ms) * 100))
                  : 0
                return (
                  <div
                    key={stage}
                    className="tech-panel"
                    style={{
                      padding: '0.65rem 0.85rem',
                      background: 'var(--bg-void)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.35rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="mono text-muted" style={{ fontSize: '10.5px', textTransform: 'uppercase' }}>
                        {stage}
                      </span>
                      <span className="mono text-dim" style={{ fontSize: '10px' }}>
                        {percentage.toFixed(0)}%
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.3rem' }}>
                      <span className="mono" style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {lat.toFixed(2)}
                      </span>
                      <span className="mono text-dim" style={{ fontSize: '10px' }}>ms</span>
                    </div>

                    {/* Proportional visual bar */}
                    <div style={{ width: '100%', height: '3px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${percentage}%`,
                          height: '100%',
                          background: stage === 'relational' ? 'var(--engine-relational)' : stage === 'graph' ? 'var(--engine-graph)' : stage === 'vector' ? 'var(--engine-vector)' : 'var(--engine-fusion)',
                        }}
                      />
                    </div>

                    {executionResult.stage_record_counts[stage] !== undefined && (
                      <span className="mono text-dim" style={{ fontSize: '9.5px' }}>
                        {executionResult.stage_record_counts[stage]} records
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Fused Results List */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.8rem' }}>
              <h3 style={{ fontSize: 'var(--text-lg)' }}>
                RRF Consensus Rankings ({executionResult.fused_results.length})
              </h3>
              <span className="mono text-muted" style={{ fontSize: '11px' }}>
                Sorted by combined RRF score descending · Click card to inspect deep metadata
              </span>
            </div>

            {executionResult.fused_results.length === 0 ? (
              <div
                className="tech-panel"
                style={{
                  padding: '2.5rem',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                }}
              >
                No projects satisfied all mandatory filters and cross-paradigm criteria.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
                {executionResult.fused_results.map((item: FusedItem) => {
                  const isExpanded = expandedEntityId === item.entity_id
                  return (
                    <div
                      key={item.entity_id}
                      className="tech-panel"
                      onClick={() => setExpandedEntityId(isExpanded ? null : item.entity_id)}
                      style={{
                        padding: '1.2rem 1.4rem',
                        background: 'var(--bg-surface)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.75rem',
                        borderLeft: '3px solid var(--accent-cyan)',
                        cursor: 'pointer',
                        transition: 'var(--transition-fast)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                          <span
                            className="mono"
                            style={{
                              fontSize: 'var(--text-lg)',
                              fontWeight: 700,
                              color: 'var(--accent-cyan)',
                              minWidth: '32px',
                            }}
                          >
                            #{item.final_rank}
                          </span>
                          <div>
                            <h4 style={{ fontSize: 'var(--text-base)', color: 'var(--text-primary)', margin: 0 }}>
                              {item.title || item.entity_id}
                            </h4>
                            <span className="mono text-muted" style={{ fontSize: '11px' }}>
                              {item.entity_id} · {item.metadata.track || 'Track'}
                            </span>
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div
                            className="mono"
                            style={{
                              padding: '0.2rem 0.6rem',
                              background: 'rgba(56, 189, 248, 0.1)',
                              border: '1px solid rgba(56, 189, 248, 0.25)',
                              borderRadius: 'var(--radius-xs)',
                              fontSize: 'var(--text-xs)',
                              color: 'var(--accent-cyan)',
                              fontWeight: 600,
                            }}
                          >
                            RRF: {item.rrf_score.toFixed(5)}
                          </div>

                          {/* Participating Engine Ranks */}
                          {Object.entries(item.engine_ranks).map(([eng, rank]) => (
                            <Badge
                              key={eng}
                              size="sm"
                              variant={eng === 'relational' ? 'cyan' : eng === 'graph' ? 'purple' : 'emerald'}
                            >
                              {eng}: #{rank}
                            </Badge>
                          ))}
                          <span style={{ fontSize: '12px', color: 'var(--text-dim)', marginLeft: '0.2rem' }}>
                            {isExpanded ? '▲' : '▼'}
                          </span>
                        </div>
                      </div>

                      {item.metadata.short_summary && (
                        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                          {item.metadata.short_summary}
                        </p>
                      )}

                      {item.metadata.tech_stack && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <span className="mono text-dim" style={{ fontSize: '10.5px' }}>STACK:</span>
                          <span className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {item.metadata.tech_stack}
                          </span>
                        </div>
                      )}

                      {/* Expanded Accordion: Deep Raw Telemetry */}
                      {isExpanded && (
                        <div
                          className="mono"
                          style={{
                            padding: '0.8rem 1rem',
                            background: 'var(--bg-void)',
                            borderTop: '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-xs)',
                            fontSize: '11px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.4rem',
                            marginTop: '0.3rem',
                          }}
                        >
                          <div style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>
                            DEEP MULTI-PARADIGM METADATA & EVIDENCE:
                          </div>
                          <div>College: <span className="text-secondary">{item.metadata.college_name || 'N/A'}</span></div>
                          <div>Team: <span className="text-secondary">{item.metadata.team_name || 'N/A'}</span></div>
                          {item.metadata.prize_category && (
                            <div>Award: <span className="text-amber">{item.metadata.prize_category}</span></div>
                          )}
                          {item.engine_scores && Object.keys(item.engine_scores).length > 0 && (
                            <div>
                              Engine Scores: {JSON.stringify(item.engine_scores)}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </section>
      )}

      {/* Session Execution History */}
      {executionHistory.length > 0 && (
        <section
          className="tech-panel"
          style={{
            padding: '1.2rem',
            background: 'var(--bg-surface-elevated)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.8rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.4rem' }}>
            <span className="mono text-muted" style={{ fontSize: '11px', textTransform: 'uppercase' }}>
              SESSION-OBSERVED EXECUTION HISTORY ({executionHistory.length} RUNS)
            </span>
            <span className="mono text-dim" style={{ fontSize: '10px' }}>
              In-memory browser session cache only (not persisted to server or disk)
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {executionHistory.map((run) => (
              <div
                key={run.id}
                className="tech-panel mono"
                style={{
                  padding: '0.5rem 0.8rem',
                  fontSize: '11px',
                  background: 'var(--bg-void)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span className="text-dim">[{run.timestamp}]</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{run.queryName}</span>
                  {run.presetId && <Badge variant="cyan" size="sm">Preset #{run.presetId}</Badge>}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                  <span className="text-muted">{run.fusedCount} records</span>
                  <span className="text-cyan">{run.totalLatencyMs.toFixed(2)} ms</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
