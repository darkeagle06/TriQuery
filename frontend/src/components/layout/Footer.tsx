import React from 'react'
import type { HealthResponse } from '../../types/api'

interface FooterProps {
  health: HealthResponse | null
}

export const Footer: React.FC<FooterProps> = ({ health }) => {
  return (
    <footer
      style={{
        borderTop: '1px solid var(--border-subtle)',
        backgroundColor: 'var(--bg-void)',
        padding: '1.2rem 0',
        marginTop: 'auto',
        fontSize: 'var(--text-xs)',
      }}
    >
      <div
        className="container"
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span className="mono" style={{ color: 'var(--accent-cyan)' }}>▲ TriQuery Core</span>
            <span className="text-muted">·</span>
            <span className="text-secondary">Multi-Paradigm Engine Architecture</span>
          </div>

          <div className="mono" style={{ color: 'var(--text-dim)', fontSize: '11px' }}>
            Backend: {health ? `${health.backend} (${health.host}:${health.port}/${health.database_name})` : 'Connecting...'}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
          <span className="mono" style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
            RRF Formulation: RRF(d) = Σ wₘ / (k + rₘ(d))
          </span>
          <span
            className="mono"
            style={{
              padding: '2px 6px',
              borderRadius: '2px',
              background: 'rgba(56, 189, 248, 0.08)',
              color: 'var(--accent-cyan)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
              fontSize: '10.5px',
            }}
          >
            PHASE 3 ACTIVE
          </span>
        </div>
      </div>
    </footer>
  )
}
