import React, { useEffect, useState } from 'react'
import type { HealthResponse, UnifiedQuery } from './types/api'
import { apiClient } from './services/api'
import { Header, type NavigationDestination } from './components/layout/Header'
import { Footer } from './components/layout/Footer'
import { ShaderBackground } from './components/layout/ShaderBackground'
import { HomeView } from './views/HomeView'
import { QueryStudioView } from './views/QueryStudioView'
import { RelationalView } from './views/RelationalView'
import { GraphView } from './views/GraphView'
import { VectorView } from './views/VectorView'
import { ExplainView } from './views/ExplainView'

export const App: React.FC = () => {
  const [currentDestination, setCurrentDestination] = useState<NavigationDestination>('home')
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthLoading, setHealthLoading] = useState<boolean>(true)
  const [healthError, setHealthError] = useState<string | null>(null)

  // Shared query state for seamless transition to ExplainView
  const [selectedQueryForExplain, setSelectedQueryForExplain] = useState<UnifiedQuery | null>(null)

  // 1. Initial health check and periodic telemetry refresh
  const checkHealth = async () => {
    setHealthLoading(true)
    setHealthError(null)
    try {
      const res = await apiClient.getHealth()
      setHealth(res)
    } catch (err: any) {
      setHealthError(err.message || 'Backend is currently offline or unreachable.')
      setHealth(null)
    } finally {
      setHealthLoading(false)
    }
  }

  useEffect(() => {
    checkHealth()
    // Periodic status polling every 30s
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  // 2. Destination View Renderer
  const renderView = () => {
    switch (currentDestination) {
      case 'home':
        return <HomeView health={health} onNavigate={setCurrentDestination} />
      case 'studio':
        return (
          <QueryStudioView
            onNavigate={setCurrentDestination}
            onSelectQueryForExplain={(q) => setSelectedQueryForExplain(q)}
          />
        )
      case 'relational':
        return <RelationalView />
      case 'graph':
        return <GraphView />
      case 'vector':
        return <VectorView />
      case 'explain':
        return <ExplainView initialQuery={selectedQueryForExplain} />
      default:
        return <HomeView health={health} onNavigate={setCurrentDestination} />
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        position: 'relative',
        zIndex: 1,
      }}
    >
      {/* Interactive Canvas Shader Field */}
      <ShaderBackground />

      {/* Top Application Header & Live Health Bar */}
      <Header
        currentDestination={currentDestination}
        onNavigate={setCurrentDestination}
        health={health}
        healthLoading={healthLoading}
        healthError={healthError}
        onRefreshHealth={checkHealth}
      />

      {/* Main Workbench View Container */}
      <main
        style={{
          flex: 1,
          paddingTop: '2rem',
          paddingBottom: '3rem',
        }}
      >
        <div className="container">
          {renderView()}
        </div>
      </main>

      {/* Persistent System Footer */}
      <Footer health={health} />
    </div>
  )
}

export default App
