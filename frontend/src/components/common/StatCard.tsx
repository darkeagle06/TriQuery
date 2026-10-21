import React from 'react'

interface StatCardProps {
  label: string
  value: string | number
  unit?: string
  subtitle?: string
  badge?: React.ReactNode
  accentColor?: string
  style?: React.CSSProperties
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  unit,
  subtitle,
  badge,
  accentColor = 'var(--accent-cyan)',
  style = {},
}) => {
  return (
    <div
      className="tech-panel tech-corner-marks"
      style={{
        padding: '1rem 1.2rem',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-sm)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        minWidth: '160px',
        ...style,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '0.45rem',
        }}
      >
        <span
          className="mono"
          style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          {label}
        </span>
        {badge}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.3rem' }}>
        <span
          className="mono"
          style={{
            fontSize: 'var(--text-2xl)',
            fontWeight: 700,
            color: accentColor,
            lineHeight: 1.1,
          }}
        >
          {value}
        </span>
        {unit && (
          <span
            className="mono"
            style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-dim)',
            }}
          >
            {unit}
          </span>
        )}
      </div>

      {subtitle && (
        <span
          style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--text-secondary)',
            marginTop: '0.35rem',
            lineHeight: 1.35,
          }}
        >
          {subtitle}
        </span>
      )}
    </div>
  )
}
