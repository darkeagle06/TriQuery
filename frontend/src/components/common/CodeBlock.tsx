import React, { useState } from 'react'

interface CodeBlockProps {
  code: string
  language?: string
  label?: string
  maxHeight?: string
  style?: React.CSSProperties
}

export const CodeBlock: React.FC<CodeBlockProps> = ({
  code,
  language = 'json',
  label,
  maxHeight = '340px',
  style = {},
}) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    })
  }

  return (
    <div
      className="tech-panel"
      style={{
        background: 'var(--bg-surface-elevated)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-sm)',
        overflow: 'hidden',
        ...style,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.4rem 0.8rem',
          background: 'rgba(0, 0, 0, 0.35)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <span
          className="mono"
          style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--accent-cyan)',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}
        >
          {label || language}
        </span>
        <button
          onClick={handleCopy}
          aria-label="Copy code to clipboard"
          className="mono"
          style={{
            fontSize: 'var(--text-xs)',
            color: copied ? 'var(--status-healthy)' : 'var(--text-secondary)',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-xs)',
            padding: '0.15rem 0.5rem',
            cursor: 'pointer',
            transition: 'var(--transition-fast)',
          }}
        >
          {copied ? '✓ COPIED' : 'COPY'}
        </button>
      </div>

      <pre
        tabIndex={0}
        style={{
          margin: 0,
          padding: '0.8rem 1rem',
          maxHeight,
          overflowY: 'auto',
          fontSize: 'var(--text-xs)',
          lineHeight: 1.55,
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-mono)',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        <code>{code}</code>
      </pre>
    </div>
  )
}
