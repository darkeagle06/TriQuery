import React, { useState } from 'react'
import type { HealthResponse } from '../../types/api'

export type NavigationDestination =
  | 'home'
  | 'studio'
  | 'relational'
  | 'graph'
  | 'vector'
  | 'explain'

interface HeaderProps {
  currentDestination: NavigationDestination
  onNavigate: (dest: NavigationDestination) => void
  health: HealthResponse | null
  healthLoading: boolean
  healthError: string | null
  onRefreshHealth: () => void
}

export const Header: React.FC<HeaderProps> = ({
  currentDestination,
  onNavigate,
  health,
  healthLoading,
  healthError,
  onRefreshHealth,
}) => {
  const [showStatusFlyout, setShowStatusFlyout] = useState(false)

  const navItems: Array<{ id: NavigationDestination; label: string; badge?: string }> = [
    { id: 'home', label: 'Overview' },
    { id: 'studio', label: 'Query Studio', badge: 'RRF' },
    { id: 'relational', label: 'Relational SQL' },
    { id: 'graph', label: 'Graph Topology' },
    { id: 'vector', label: 'Vector Search' },
    { id: 'explain', label: 'Explainability' },
  ]

  const isHealthy = health?.is_healthy === true
  const isDegraded = health?.status === 'degraded'

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        backgroundColor: 'var(--bg-glass-elevated)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      <div
        className="container"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: '62px',
          gap: '1.5rem',
        }}
      >
        {/* Brand / Logo */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.8rem',
            cursor: 'pointer',
          }}
          onClick={() => onNavigate('home')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onNavigate('home')}
        >
          {/* Geometric Triangle Mark */}
          <div
            style={{
              width: '28px',
              height: '28px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%)',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              borderRadius: 'var(--radius-xs)',
              position: 'relative',
            }}
          >
            <span
              className="mono"
              style={{
                fontSize: '15px',
                color: 'var(--accent-cyan)',
                fontWeight: 700,
                transform: 'translateY(-1px)',
              }}
            >
              ▲
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <span
                style={{
                  fontSize: 'var(--text-lg)',
                  fontWeight: 700,
                  letterSpacing: '-0.03em',
                  color: 'var(--text-primary)',
                }}
              >
                TriQuery
              </span>
              <span
                className="mono"
                style={{
                  fontSize: '10px',
                  padding: '1px 5px',
                  borderRadius: '2px',
                  background: 'rgba(255, 255, 255, 0.06)',
                  color: 'var(--text-muted)',
                }}
              >
                v1.0
              </span>
            </div>
            <span
              className="mono"
              style={{
                fontSize: '9.5px',
                color: 'var(--text-dim)',
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
              }}
            >
              Multi-Paradigm Engine
            </span>
          </div>
        </div>

        {/* Navigation Destinations */}
        <nav
          aria-label="Primary navigation"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
            overflowX: 'auto',
          }}
        >
          {navItems.map((item) => {
            const isActive = currentDestination === item.id
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                style={{
                  position: 'relative',
                  padding: '0.45rem 0.8rem',
                  fontSize: 'var(--text-sm)',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  background: isActive ? 'rgba(255, 255, 255, 0.06)' : 'transparent',
                  border: isActive ? '1px solid var(--border-medium)' : '1px solid transparent',
                  transition: 'var(--transition-fast)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  whiteSpace: 'nowrap',
                }}
              >
                {item.label}
                {item.badge && (
                  <span
                    className="mono"
                    style={{
                      fontSize: '9px',
                      padding: '1px 4px',
                      borderRadius: '2px',
                      background: isActive ? 'var(--accent-cyan-dim)' : 'rgba(255, 255, 255, 0.04)',
                      color: isActive ? 'var(--accent-cyan)' : 'var(--text-muted)',
                      border: isActive ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid var(--border-subtle)',
                    }}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {/* Live System Health Pill */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setShowStatusFlyout(!showStatusFlyout)}
            aria-label="Toggle system status details"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.55rem',
              padding: '0.35rem 0.75rem',
              background: 'var(--bg-surface-elevated)',
              border: `1px solid ${isHealthy ? 'rgba(16, 185, 129, 0.25)' : isDegraded ? 'rgba(245, 158, 11, 0.25)' : 'rgba(239, 68, 68, 0.3)'}`,
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              transition: 'var(--transition-fast)',
            }}
          >
            <span
              aria-hidden="true"
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: isHealthy ? 'var(--status-healthy)' : isDegraded ? 'var(--status-warning)' : 'var(--status-error)',
                boxShadow: `0 0 8px ${isHealthy ? 'var(--status-healthy)' : isDegraded ? 'var(--status-warning)' : 'var(--status-error)'}`,
              }}
            />
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
              <span
                className="mono"
                style={{
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  color: isHealthy ? 'var(--text-primary)' : '#fca5a5',
                  lineHeight: 1.2,
                }}
              >
                {healthLoading
                  ? 'SYNCING...'
                  : health
                    ? `${health.backend} [ONLINE]`
                    : 'OFFLINE'}
              </span>
              <span
                className="mono"
                style={{
                  fontSize: '9.5px',
                  color: 'var(--text-dim)',
                  lineHeight: 1.1,
                }}
              >
                {health ? `${health.graph.node_count} nodes · ${health.vector.document_count} docs` : 'API disconnected'}
              </span>
            </div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>▾</span>
          </button>

          {/* Quick Diagnostics Flyout */}
          {showStatusFlyout && (
            <div
              className="tech-panel"
              style={{
                position: 'absolute',
                top: 'calc(100% + 8px)',
                right: 0,
                width: '320px',
                padding: '1rem',
                background: 'var(--bg-surface-elevated)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-medium)',
                zIndex: 100,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '0.8rem',
                  paddingBottom: '0.5rem',
                  borderBottom: '1px solid var(--border-subtle)',
                }}
              >
                <span className="mono" style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                  SYSTEM TELEMETRY
                </span>
                <button
                  onClick={onRefreshHealth}
                  className="mono"
                  style={{
                    fontSize: '10px',
                    color: 'var(--text-secondary)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    padding: '2px 6px',
                    borderRadius: '2px',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  REFRESH
                </button>
              </div>

              {health ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: 'var(--text-xs)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-secondary">Backend Driver:</span>
                    <span className="mono text-cyan">{health.backend}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-secondary">Database:</span>
                    <span className="mono">{health.database_name}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-secondary">Host / Port:</span>
                    <span className="mono">{health.host}:{health.port}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-secondary">Graph Nodes / Edges:</span>
                    <span className="mono text-indigo">{health.graph.node_count} / {health.graph.edge_count}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-secondary">Vector Documents:</span>
                    <span className="mono text-emerald">{health.vector.document_count} projects</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-secondary">Vector Provider:</span>
                    <span className="mono" style={{ fontSize: '10.5px' }}>{health.vector.is_semantic ? 'Dense Neural Embeddings' : 'TF-IDF Cosine Similarity'}</span>
                  </div>

                  <div style={{ marginTop: '0.4rem', paddingTop: '0.4rem', borderTop: '1px solid var(--border-subtle)' }}>
                    <span className="mono text-muted" style={{ fontSize: '10px' }}>
                      TABLE RECORD COUNTS:
                    </span>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.2rem', marginTop: '0.3rem' }}>
                      {Object.entries(health.table_counts).map(([tbl, count]) => (
                        <div key={tbl} className="mono" style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>
                          {tbl}: <strong style={{ color: 'var(--text-primary)' }}>{count}</strong>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: 'var(--text-xs)', color: '#fca5a5' }}>
                  {healthError || 'Unable to connect to FastAPI backend at http://127.0.0.1:8000. Please start the backend service.'}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
