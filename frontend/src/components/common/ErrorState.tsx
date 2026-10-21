import React from 'react'
import { Button } from './Button'

interface ErrorStateProps {
  title?: string
  message: string
  detail?: string
  onRetry?: () => void
  isRetrying?: boolean
  style?: React.CSSProperties
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Backend Connectivity Error',
  message,
  detail,
  onRetry,
  isRetrying = false,
  style = {},
}) => {
  return (
    <div
      className="tech-panel"
      role="alert"
      style={{
        padding: '1.4rem 1.6rem',
        background: 'rgba(239, 68, 68, 0.05)',
        border: '1px solid rgba(239, 68, 68, 0.25)',
        borderRadius: 'var(--radius-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        ...style,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <span
          aria-hidden="true"
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: 'var(--status-error)',
            boxShadow: '0 0 8px var(--status-error)',
          }}
        />
        <h4 style={{ fontSize: 'var(--text-base)', color: '#fca5a5', fontWeight: 600 }}>
          {title}
        </h4>
      </div>

      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', margin: 0 }}>
        {message}
      </p>

      {detail && (
        <pre
          className="mono"
          style={{
            fontSize: 'var(--text-xs)',
            padding: '0.5rem 0.8rem',
            background: 'rgba(0, 0, 0, 0.4)',
            border: '1px solid rgba(239, 68, 68, 0.15)',
            borderRadius: 'var(--radius-xs)',
            color: '#f87171',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {detail}
        </pre>
      )}

      {onRetry && (
        <div style={{ marginTop: '0.3rem' }}>
          <Button
            variant="secondary"
            size="sm"
            onClick={onRetry}
            loading={isRetrying}
            style={{
              borderColor: 'rgba(239, 68, 68, 0.35)',
              color: '#fca5a5',
            }}
          >
            Retry Connection
          </Button>
        </div>
      )}
    </div>
  )
}
