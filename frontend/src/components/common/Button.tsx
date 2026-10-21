import React from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: React.ReactNode
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  disabled,
  style = {},
  ...props
}) => {
  const getVariantStyles = (): React.CSSProperties => {
    switch (variant) {
      case 'primary':
        return {
          background: 'linear-gradient(135deg, var(--accent-cyan) 0%, #0284c7 100%)',
          color: '#040711',
          border: '1px solid rgba(56, 189, 248, 0.4)',
          fontWeight: 600,
          boxShadow: '0 1px 8px rgba(56, 189, 248, 0.25)',
        }
      case 'secondary':
        return {
          background: 'var(--bg-surface-elevated)',
          color: 'var(--text-primary)',
          border: '1px solid var(--border-medium)',
        }
      case 'outline':
        return {
          background: 'transparent',
          color: 'var(--accent-cyan)',
          border: '1px solid var(--accent-cyan)',
        }
      case 'ghost':
        return {
          background: 'transparent',
          color: 'var(--text-secondary)',
          border: '1px solid transparent',
        }
    }
  }

  const getSizeStyles = (): React.CSSProperties => {
    switch (size) {
      case 'sm':
        return {
          padding: '0.35rem 0.65rem',
          fontSize: 'var(--text-xs)',
          gap: '0.35rem',
        }
      case 'lg':
        return {
          padding: '0.65rem 1.4rem',
          fontSize: 'var(--text-base)',
          gap: '0.55rem',
        }
      case 'md':
      default:
        return {
          padding: '0.45rem 0.95rem',
          fontSize: 'var(--text-sm)',
          gap: '0.45rem',
        }
    }
  }

  return (
    <button
      disabled={disabled || loading}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 'var(--radius-sm)',
        letterSpacing: '0.01em',
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.45 : 1,
        transition: 'var(--transition-fast)',
        userSelect: 'none',
        ...getVariantStyles(),
        ...getSizeStyles(),
        ...style,
      }}
      {...props}
    >
      {loading ? (
        <span
          aria-hidden="true"
          style={{
            width: '12px',
            height: '12px',
            border: '2px solid currentColor',
            borderTopColor: 'transparent',
            borderRadius: '50%',
            animation: 'spin 0.6s linear infinite',
            marginRight: '0.2rem',
          }}
        />
      ) : icon ? (
        <span aria-hidden="true">{icon}</span>
      ) : null}
      {children}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </button>
  )
}
