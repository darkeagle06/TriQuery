import React, { useState } from 'react'
import type { VectorSearchItem, VectorSearchResponse } from '../types/api'
import { apiClient } from '../services/api'
import { Badge } from '../components/common/Badge'
import { Button } from '../components/common/Button'
import { ErrorState } from '../components/common/ErrorState'

export const VectorView: React.FC = () => {
  const [queryText, setQueryText] = useState<string>('autonomous drone navigation visual SLAM')
  const [topK, setTopK] = useState<number>(5)
  const [minScore, setMinScore] = useState<number>(0.0)

  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [searchResult, setSearchResult] = useState<VectorSearchResponse | null>(null)

  const samplePrompts = [
    'autonomous drone navigation obstacle avoidance',
    'pulmonary chest X-ray pneumonia diagnosis deep learning',
    'AI solutions for urban traffic congestion monitoring',
    'zero-knowledge proof healthcare verification',
  ]

  const handleSearch = async (text = queryText, k = topK, minSc = minScore) => {
    if (!text.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.searchVectors(text.trim(), k, minSc)
      setSearchResult(res)
    } catch (err: any) {
      setError(err.message || 'Vector search failed on backend.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem', paddingBottom: '4rem' }}>
      {/* View Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
          <Badge variant="emerald" size="sm">PARADIGM 3: VECTOR SIMILARITY</Badge>
          <span className="mono text-muted" style={{ fontSize: 'var(--text-xs)' }}>
            TF-IDF High-Dimensional Lexical Cosine Index
          </span>
        </div>
        <h1 style={{ fontSize: 'var(--text-3xl)' }}>Vector Similarity Search Console</h1>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
          Discover projects through conceptual semantic proximity over project descriptions and technology stacks.
        </p>
      </div>

      {/* Search Input Console */}
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <label className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            NATURAL LANGUAGE SEMANTIC QUERY (POST /api/vector/search)
          </label>
          <div style={{ display: 'flex', gap: '0.6rem' }}>
            <input
              type="text"
              placeholder="Describe concepts, technologies, or domain problems..."
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              style={{
                flex: 1,
                fontSize: 'var(--text-base)',
                padding: '0.65rem 0.95rem',
              }}
            />
            <Button
              variant="primary"
              onClick={() => handleSearch()}
              loading={loading}
              icon={<span className="mono">🔍</span>}
            >
              Search Vectors
            </Button>
          </div>
        </div>

        {/* Preset Query Chips */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span className="mono text-dim" style={{ fontSize: '11px' }}>Sample Prompts:</span>
          {samplePrompts.map((prompt) => (
            <button
              key={prompt}
              onClick={() => {
                setQueryText(prompt)
                handleSearch(prompt)
              }}
              className="mono"
              style={{
                fontSize: '11px',
                padding: '0.25rem 0.6rem',
                borderRadius: 'var(--radius-xs)',
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
              }}
            >
              "{prompt}"
            </button>
          ))}
        </div>

        {/* Search Parameter Sliders */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '1.5rem',
            paddingTop: '0.8rem',
            borderTop: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="mono text-muted" style={{ fontSize: '11px' }}>Top-K Limit:</span>
              <span className="mono text-emerald" style={{ fontSize: '11px', fontWeight: 600 }}>{topK} results</span>
            </div>
            <input
              type="range"
              min="1"
              max="20"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="mono text-muted" style={{ fontSize: '11px' }}>Min Cosine Score Cutoff:</span>
              <span className="mono text-emerald" style={{ fontSize: '11px', fontWeight: 600 }}>{minScore.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="0.8"
              step="0.05"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
            />
          </div>
        </div>
      </section>

      {/* Error State */}
      {error && <ErrorState message={error} onRetry={() => handleSearch()} isRetrying={loading} />}

      {/* Search Results */}
      {searchResult && (
        <section style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem' }}>
            <div>
              <h3 style={{ fontSize: 'var(--text-lg)' }}>
                Nearest Neighbor Candidates ({searchResult.count})
              </h3>
              <span className="mono text-muted" style={{ fontSize: 'var(--text-xs)' }}>
                Provider: {searchResult.provider}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Badge variant="emerald" size="sm">
                Latency: {searchResult.execution_time_ms.toFixed(3)} ms
              </Badge>
            </div>
          </div>

          {searchResult.results.length === 0 ? (
            <div className="tech-panel mono text-muted" style={{ padding: '2rem', textAlign: 'center' }}>
              No project documents matched similarity cutoff ≥ {minScore}.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
              {searchResult.results.map((item: VectorSearchItem) => {
                const scorePercent = Math.min(100, Math.max(0, item.score * 100))
                return (
                  <div
                    key={item.entity_id}
                    className="tech-panel"
                    style={{
                      padding: '1.2rem 1.4rem',
                      background: 'var(--bg-surface)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.65rem',
                      borderLeft: '3px solid var(--engine-vector)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                        <span
                          className="mono"
                          style={{
                            fontSize: 'var(--text-base)',
                            fontWeight: 700,
                            color: 'var(--engine-vector)',
                            minWidth: '28px',
                          }}
                        >
                          #{item.rank}
                        </span>
                        <div>
                          <h4 style={{ fontSize: 'var(--text-base)', color: 'var(--text-primary)', margin: 0 }}>
                            {item.title}
                          </h4>
                          <span className="mono text-muted" style={{ fontSize: '11px' }}>
                            {item.entity_id} {item.track && `· ${item.track}`}
                          </span>
                        </div>
                      </div>

                      {/* Cosine Score Visual Indicator */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', minWidth: '160px' }}>
                        <div
                          style={{
                            flex: 1,
                            height: '6px',
                            background: 'rgba(255, 255, 255, 0.08)',
                            borderRadius: '3px',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              width: `${scorePercent}%`,
                              height: '100%',
                              background: 'var(--engine-vector)',
                            }}
                          />
                        </div>
                        <span className="mono text-emerald" style={{ fontSize: 'var(--text-xs)', fontWeight: 600 }}>
                          {item.score.toFixed(4)}
                        </span>
                      </div>
                    </div>

                    {item.short_summary && (
                      <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                        {item.short_summary}
                      </p>
                    )}

                    {item.tech_stack && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <span className="mono text-dim" style={{ fontSize: '10px' }}>TECH STACK:</span>
                        <span className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {item.tech_stack}
                        </span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
