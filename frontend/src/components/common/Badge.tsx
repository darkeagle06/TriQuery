import React from 'react'

export type BadgeVariant =
  | 'cyan'
  | 'indigo'
  | 'emerald'
  | 'amber'
  | 'purple'
  | 'muted'
  | 'healthy'
  | 'warning'
  | 'error'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  size?: 'sm' | 'md'
  dot?: boolean
  className?: string
  style?: React.CSSProperties
}

const variantStyles: Record<BadgeVariant, { bg: string; text: string; border: string; dotColor?: string }> = {
  cyan: {
    bg: 'var(--accent-cyan-dim)',
    text: 'var(--accent-cyan)',
    border: 'rgba(56, 189, 248, 0.28)',
    dotColor: 'var(--accent-cyan)',
  },
  indigo: {
    bg: 'var(--accent-indigo-dim)',
    text: 'var(--accent-indigo)',
    border: 'rgba(99, 102, 241, 0.28)',
    dotColor: 'var(--accent-indigo)',
  },
  emerald: {
    bg: 'var(--engine-vector-dim)',
    text: 'var(--engine-vector)',
    border: 'rgba(16, 185, 129, 0.28)',
    dotColor: 'var(--engine-vector)',
  },
  amber: {
    bg: 'var(--engine-fusion-dim)',
    text: 'var(--engine-fusion)',
    border: 'rgba(245, 158, 11, 0.28)',
    dotColor: 'var(--engine-fusion)',
  },
  purple: {
    bg: 'var(--engine-graph-dim)',
    text: 'var(--engine-graph)',
    border: 'rgba(168, 85, 247, 0.28)',
    dotColor: 'var(--engine-graph)',
  },
  muted: {
    bg: 'rgba(255, 255, 255, 0.04)',
    text: 'var(--text-secondary)',
    border: 'var(--border-subtle)',
    dotColor: 'var(--text-dim)',
  },
  healthy: {
    bg: 'var(--status-healthy-dim)',
    text: 'var(--status-healthy)',
    border: 'rgba(16, 185, 129, 0.3)',
    dotColor: 'var(--status-healthy)',
  },
  warning: {
    bg: 'var(--status-warning-dim)',
    text: 'var(--status-warning)',
    border: 'rgba(245, 158, 11, 0.3)',
    dotColor: 'var(--status-warning)',
  },
  error: {
    bg: 'var(--status-error-dim)',
    text: 'var(--status-error)',
    border: 'rgba(239, 68, 68, 0.3)',
    dotColor: 'var(--status-error)',
  },
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'cyan',
  size = 'md',
  dot = false,
  className = '',
  style = {},
}) => {
  const v = variantStyles[variant] || variantStyles.cyan
  const isSm = size === 'sm'

  return (
    <span
      className={`mono ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        padding: isSm ? '0.12rem 0.45rem' : '0.2rem 0.6rem',
        fontSize: isSm ? 'var(--text-xs)' : 'var(--text-sm)',
        lineHeight: 1.2,
        fontWeight: 500,
        borderRadius: 'var(--radius-sm)',
        background: v.bg,
        color: v.text,
        border: `1px solid ${v.border}`,
        letterSpacing: '0.02em',
        userSelect: 'none',
        whiteSpace: 'nowrap',
        ...style,
      }}
    >
      {dot && (
        <span
          aria-hidden="true"
          style={{
            width: isSm ? '5px' : '6px',
            height: isSm ? '5px' : '6px',
            borderRadius: '50%',
            backgroundColor: v.dotColor || v.text,
            boxShadow: `0 0 6px ${v.dotColor || v.text}`,
          }}
        />
      )}
      {children}
    </span>
  )
}
