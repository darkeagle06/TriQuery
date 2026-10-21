import React, { useEffect, useState } from 'react'
import type { ProjectRecord, TableSchema, TablesResponse } from '../types/api'
import { apiClient } from '../services/api'
import { Badge } from '../components/common/Badge'
import { Button } from '../components/common/Button'
import { ErrorState } from '../components/common/ErrorState'

export const RelationalView: React.FC = () => {
  const [tablesData, setTablesData] = useState<TablesResponse | null>(null)
  const [selectedTable, setSelectedTable] = useState<string>('projects')
  const [loadingTables, setLoadingTables] = useState<boolean>(true)
  const [tablesError, setTablesError] = useState<string | null>(null)

  // Project filtering state
  const [projects, setProjects] = useState<ProjectRecord[]>([])
  const [trackFilter, setTrackFilter] = useState<string>('')
  const [collegeFilter, setCollegeFilter] = useState<string>('')
  const [loadingProjects, setLoadingProjects] = useState<boolean>(false)
  const [projectsError, setProjectsError] = useState<string | null>(null)

  // 1. Fetch tables metadata
  const fetchTables = async () => {
    setLoadingTables(true)
    setTablesError(null)
    try {
      const res = await apiClient.getRelationalTables()
      setTablesData(res)
      if (res.tables.length > 0 && !res.tables.some((t) => t.table_name === selectedTable)) {
        setSelectedTable(res.tables[0].table_name)
      }
    } catch (err: any) {
      setTablesError(err.message || 'Failed to fetch table schema from backend.')
    } finally {
      setLoadingTables(false)
    }
  }

  // 2. Fetch projects
  const fetchProjects = async (track = trackFilter, college = collegeFilter) => {
    setLoadingProjects(true)
    setProjectsError(null)
    try {
      const res = await apiClient.getRelationalProjects({
        track: track.trim() || undefined,
        college: college.trim() || undefined,
      })
      setProjects(res.data)
    } catch (err: any) {
      setProjectsError(err.message || 'Failed to fetch filtered projects.')
    } finally {
      setLoadingProjects(false)
    }
  }

  useEffect(() => {
    fetchTables()
    fetchProjects()
  }, [])

  const currentTableSchema: TableSchema | undefined = tablesData?.tables.find(
    (t) => t.table_name === selectedTable
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem', paddingBottom: '4rem' }}>
      {/* View Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
          <Badge variant="cyan" size="sm">PARADIGM 1: RELATIONAL SQL</Badge>
          <span className="mono text-muted" style={{ fontSize: 'var(--text-xs)' }}>
            MySQL 8.x information_schema
          </span>
        </div>
        <h1 style={{ fontSize: 'var(--text-3xl)' }}>Relational Schema & Records Explorer</h1>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
          Inspect live table constraints, column types, foreign keys, and execute parameterized filter queries.
        </p>
      </div>

      {/* Schema Metadata Section */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 style={{ fontSize: 'var(--text-xl)' }}>Database Schema Metadata</h2>
          {tablesData && (
            <span className="mono text-muted" style={{ fontSize: 'var(--text-xs)' }}>
              Database: <strong className="text-cyan">{tablesData.database}</strong> ({tablesData.table_count} tables)
            </span>
          )}
        </div>

        {loadingTables ? (
          <div className="tech-panel mono text-muted" style={{ padding: '2rem', textAlign: 'center' }}>
            Querying MySQL information_schema metadata...
          </div>
        ) : tablesError ? (
          <ErrorState message={tablesError} onRetry={fetchTables} isRetrying={loadingTables} />
        ) : tablesData ? (
          <div className="tech-panel" style={{ padding: '1.2rem', background: 'var(--bg-surface-elevated)' }}>
            {/* Table Selection Tabs */}
            <div
              style={{
                display: 'flex',
                gap: '0.4rem',
                overflowX: 'auto',
                paddingBottom: '0.6rem',
                borderBottom: '1px solid var(--border-subtle)',
                marginBottom: '1rem',
              }}
            >
              {tablesData.tables.map((t) => {
                const isSelected = selectedTable === t.table_name
                return (
                  <button
                    key={t.table_name}
                    onClick={() => setSelectedTable(t.table_name)}
                    className="mono"
                    style={{
                      padding: '0.35rem 0.75rem',
                      fontSize: 'var(--text-xs)',
                      background: isSelected ? 'var(--accent-cyan-dim)' : 'transparent',
                      color: isSelected ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                      border: `1px solid ${isSelected ? 'rgba(56, 189, 248, 0.4)' : 'transparent'}`,
                      borderRadius: 'var(--radius-xs)',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                    }}
                  >
                    <span>{t.table_name}</span>
                    <span
                      style={{
                        fontSize: '9.5px',
                        padding: '1px 4px',
                        borderRadius: '2px',
                        background: 'rgba(255, 255, 255, 0.06)',
                        color: 'var(--text-muted)',
                      }}
                    >
                      {t.row_count}
                    </span>
                  </button>
                )
              })}
            </div>

            {/* Table Column & Foreign Key Inspector */}
            {currentTableSchema && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span className="mono text-cyan" style={{ fontSize: 'var(--text-sm)', fontWeight: 600 }}>
                    TABLE: {currentTableSchema.table_name} ({currentTableSchema.columns.length} columns, {currentTableSchema.row_count} rows)
                  </span>
                  {currentTableSchema.foreign_keys.length > 0 && (
                    <Badge variant="purple" size="sm">
                      {currentTableSchema.foreign_keys.length} Foreign Keys
                    </Badge>
                  )}
                </div>

                {/* Columns Table */}
                <div style={{ overflowX: 'auto' }}>
                  <table
                    className="mono"
                    style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: 'var(--text-xs)',
                    }}
                  >
                    <thead>
                      <tr style={{ background: 'rgba(0, 0, 0, 0.3)', borderBottom: '1px solid var(--border-medium)', textAlign: 'left' }}>
                        <th style={{ padding: '0.5rem 0.8rem', color: 'var(--text-muted)' }}>COLUMN</th>
                        <th style={{ padding: '0.5rem 0.8rem', color: 'var(--text-muted)' }}>DATA TYPE</th>
                        <th style={{ padding: '0.5rem 0.8rem', color: 'var(--text-muted)' }}>KEY</th>
                        <th style={{ padding: '0.5rem 0.8rem', color: 'var(--text-muted)' }}>NULLABLE</th>
                        <th style={{ padding: '0.5rem 0.8rem', color: 'var(--text-muted)' }}>DEFAULT</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentTableSchema.columns.map((c) => (
                        <tr
                          key={c.name}
                          style={{
                            borderBottom: '1px solid var(--border-subtle)',
                            background: c.primary_key ? 'rgba(56, 189, 248, 0.03)' : 'transparent',
                          }}
                        >
                          <td style={{ padding: '0.5rem 0.8rem', color: 'var(--text-primary)', fontWeight: c.primary_key ? 600 : 400 }}>
                            {c.name}
                          </td>
                          <td style={{ padding: '0.5rem 0.8rem', color: 'var(--accent-cyan)' }}>
                            {c.type}
                          </td>
                          <td style={{ padding: '0.5rem 0.8rem' }}>
                            {c.primary_key ? (
                              <Badge variant="cyan" size="sm">PRIMARY</Badge>
                            ) : (
                              <span className="text-dim">—</span>
                            )}
                          </td>
                          <td style={{ padding: '0.5rem 0.8rem', color: c.nullable ? 'var(--text-secondary)' : 'var(--text-dim)' }}>
                            {c.nullable ? 'YES' : 'NO'}
                          </td>
                          <td style={{ padding: '0.5rem 0.8rem', color: 'var(--text-dim)' }}>
                            {c.default !== null ? c.default : 'NULL'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Foreign Keys Summary */}
                {currentTableSchema.foreign_keys.length > 0 && (
                  <div
                    style={{
                      padding: '0.8rem 1rem',
                      background: 'rgba(168, 85, 247, 0.05)',
                      border: '1px solid rgba(168, 85, 247, 0.2)',
                      borderRadius: 'var(--radius-sm)',
                    }}
                  >
                    <span className="mono text-purple" style={{ fontSize: '11px', fontWeight: 600 }}>
                      FOREIGN KEY RELATIONSHIPS:
                    </span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', marginTop: '0.4rem' }}>
                      {currentTableSchema.foreign_keys.map((fk, idx) => (
                        <div key={idx} className="mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                          • <strong style={{ color: 'var(--text-primary)' }}>{fk.column}</strong> → references{' '}
                          <span className="text-purple">{fk.referenced_table}.{fk.referenced_column}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : null}
      </section>

      {/* Live Projects Query & Parameterized Filter Section */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem' }}>
          <div>
            <h2 style={{ fontSize: 'var(--text-xl)' }}>Live Project Filter Query</h2>
            <span className="mono text-muted" style={{ fontSize: 'var(--text-xs)' }}>
              GET /api/relational/projects (Parameterized SQL Join)
            </span>
          </div>

          <span className="mono text-cyan" style={{ fontSize: 'var(--text-xs)' }}>
            {projects.length} projects matched
          </span>
        </div>

        {/* Filter Controls */}
        <div
          className="tech-panel"
          style={{
            padding: '1.2rem',
            background: 'var(--bg-surface)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'flex-end',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', flex: 1, minWidth: '200px' }}>
            <label className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              FILTER BY TRACK
            </label>
            <input
              type="text"
              placeholder="e.g. Robotics & AI, Healthcare & AI..."
              value={trackFilter}
              onChange={(e) => setTrackFilter(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchProjects()}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', flex: 1, minWidth: '200px' }}>
            <label className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              FILTER BY COLLEGE
            </label>
            <input
              type="text"
              placeholder="e.g. IIT Delhi, IIT Bombay, BITS Pilani..."
              value={collegeFilter}
              onChange={(e) => setCollegeFilter(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchProjects()}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button
              variant="primary"
              onClick={() => fetchProjects()}
              loading={loadingProjects}
            >
              Filter SQL
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setTrackFilter('')
                setCollegeFilter('')
                fetchProjects('', '')
              }}
            >
              Reset
            </Button>
          </div>
        </div>

        {/* Projects Error */}
        {projectsError && (
          <ErrorState message={projectsError} onRetry={() => fetchProjects()} isRetrying={loadingProjects} />
        )}

        {/* Project Records Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))',
            gap: '1rem',
          }}
        >
          {projects.map((proj) => (
            <div
              key={proj.project_id}
              className="tech-panel"
              style={{
                padding: '1.2rem',
                background: 'var(--bg-surface-elevated)',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.7rem',
                borderLeft: '3px solid var(--engine-relational)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="mono text-cyan" style={{ fontSize: 'var(--text-xs)', fontWeight: 600 }}>
                  project:{proj.project_id}
                </span>
                <Badge variant="cyan" size="sm">
                  {proj.track}
                </Badge>
              </div>

              <h4 style={{ fontSize: 'var(--text-base)', color: 'var(--text-primary)', margin: 0 }}>
                {proj.project_title}
              </h4>

              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                {proj.short_summary}
              </p>

              <div
                className="mono text-muted"
                style={{
                  fontSize: '11px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.2rem',
                  marginTop: 'auto',
                  paddingTop: '0.6rem',
                  borderTop: '1px solid var(--border-subtle)',
                }}
              >
                <div>Team: <strong style={{ color: 'var(--text-primary)' }}>{proj.team_name}</strong></div>
                <div>College: <span className="text-secondary">{proj.college_name} ({proj.college_city})</span></div>
                <div>Hackathon: {proj.hackathon_name} ({proj.hackathon_year})</div>
                {proj.prize_category && (
                  <div style={{ color: 'var(--engine-fusion)', marginTop: '0.2rem' }}>
                    Award: {proj.prize_category} (₹{proj.cash_prize})
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
