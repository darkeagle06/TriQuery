import React, { useEffect, useRef, useState } from 'react'
import type { GraphEdgeItem, GraphNodeItem, GraphPathResponse, GraphTopologyResponse } from '../types/api'
import { apiClient } from '../services/api'
import { Badge } from '../components/common/Badge'
import { Button } from '../components/common/Button'
import { ErrorState } from '../components/common/ErrorState'
import { StatCard } from '../components/common/StatCard'

interface SimNode extends GraphNodeItem {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  color: string
}

const TYPE_COLORS: Record<string, string> = {
  participant: '#38bdf8', // Spectral Cyan
  college: '#6366f1',     // Indigo
  team: '#a855f7',        // Violet
  project: '#10b981',     // Emerald
  hackathon: '#f59e0b',   // Amber
  award: '#ec4899',       // Pink
}

export const GraphView: React.FC = () => {
  const [topology, setTopology] = useState<GraphTopologyResponse | null>(null)
  const [loadingTopology, setLoadingTopology] = useState<boolean>(true)
  const [topologyError, setTopologyError] = useState<string | null>(null)

  // Interactive Graph Controls
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [selectedNode, setSelectedNode] = useState<SimNode | null>(null)
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('all')

  // Shortest Path state
  const [sourceNode, setSourceNode] = useState<string>('participant:1')
  const [targetNode, setTargetNode] = useState<string>('participant:5')
  const [directed, setDirected] = useState<boolean>(false)
  const [pathResult, setPathResult] = useState<GraphPathResponse | null>(null)
  const [loadingPath, setLoadingPath] = useState<boolean>(false)
  const [pathError, setPathError] = useState<string | null>(null)

  // Graph Simulation State (stored in refs for high-FPS animation loop)
  const nodesRef = useRef<SimNode[]>([])
  const edgesRef = useRef<GraphEdgeItem[]>([])
  const transformRef = useRef<{ x: number; y: number; zoom: number }>({ x: 0, y: 0, zoom: 1 })
  const isDraggingRef = useRef<boolean>(false)
  const draggedNodeRef = useRef<SimNode | null>(null)
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 })

  // 1. Fetch Topology from API
  const fetchTopology = async () => {
    setLoadingTopology(true)
    setTopologyError(null)
    try {
      const res = await apiClient.getGraphTopology(500)
      setTopology(res)

      // Initialize Simulation Nodes with circular spatial layout
      const width = 800
      const height = 500
      const numNodes = res.nodes.length
      const initializedNodes: SimNode[] = res.nodes.map((n, i) => {
        const angle = (i / numNodes) * Math.PI * 2
        const radius = 180 + (i % 3) * 60
        return {
          ...n,
          x: width * 0.5 + Math.cos(angle) * radius,
          y: height * 0.5 + Math.sin(angle) * radius,
          vx: 0,
          vy: 0,
          radius: n.node_type === 'project' || n.node_type === 'college' ? 16 : 12,
          color: TYPE_COLORS[n.node_type] || '#94a3b8',
        }
      })

      nodesRef.current = initializedNodes
      edgesRef.current = res.edges
      transformRef.current = { x: 0, y: 0, zoom: 1 }
    } catch (err: any) {
      setTopologyError(err.message || 'Failed to fetch graph topology from API.')
    } finally {
      setLoadingTopology(false)
    }
  }

  // 2. Compute Shortest Path via API
  const handleFindPath = async () => {
    if (!sourceNode.trim() || !targetNode.trim()) return
    setLoadingPath(true)
    setPathError(null)
    try {
      const res = await apiClient.findGraphPath(sourceNode.trim(), targetNode.trim(), directed)
      setPathResult(res)
    } catch (err: any) {
      setPathError(err.message || 'Path traversal failed on graph engine.')
    } finally {
      setLoadingPath(false)
    }
  }

  useEffect(() => {
    fetchTopology()
  }, [])

  // 3. Canvas Simulation & Rendering Loop
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationFrameId: number

    // Physical Force parameters
    const repulsion = 450
    const springLength = 80
    const damping = 0.88
    const centerGravity = 0.02

    const render = () => {
      const width = (canvas.width = canvas.clientWidth)
      const height = (canvas.height = canvas.clientHeight)

      const nodes = nodesRef.current
      const edges = edgesRef.current
      const transform = transformRef.current
      const pathSet = new Set(pathResult?.found ? pathResult.path : [])

      // Step 1: Force-directed physics step
      const cx = width * 0.5
      const cy = height * 0.5

      for (let i = 0; i < nodes.length; i++) {
        const n1 = nodes[i]

        // Gravity to center
        n1.vx += (cx - n1.x) * centerGravity
        n1.vy += (cy - n1.y) * centerGravity

        // Node repulsion
        for (let j = i + 1; j < nodes.length; j++) {
          const n2 = nodes[j]
          const dx = n2.x - n1.x
          const dy = n2.y - n1.y
          const dist = Math.hypot(dx, dy) || 1
          if (dist < 260) {
            const force = repulsion / (dist * dist)
            const fx = (dx / dist) * force
            const fy = (dy / dist) * force
            n1.vx -= fx
            n1.vy -= fy
            n2.vx += fx
            n2.vy += fy
          }
        }
      }

      // Edge spring attraction
      const nodeMap = new Map<string, SimNode>()
      nodes.forEach((n) => nodeMap.set(n.id, n))

      edges.forEach((e) => {
        const source = nodeMap.get(e.source)
        const target = nodeMap.get(e.target)
        if (source && target) {
          const dx = target.x - source.x
          const dy = target.y - source.y
          const dist = Math.hypot(dx, dy) || 1
          const force = (dist - springLength) * 0.04
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force
          source.vx += fx
          source.vy += fy
          target.vx -= fx
          target.vy -= fy
        }
      })

      // Update positions
      nodes.forEach((n) => {
        if (n !== draggedNodeRef.current) {
          n.vx *= damping
          n.vy *= damping
          n.x += n.vx
          n.y += n.vy
        }
      })

      // Step 2: Clear & apply pan/zoom transform
      ctx.clearRect(0, 0, width, height)
      ctx.save()
      ctx.translate(transform.x, transform.y)
      ctx.scale(transform.zoom, transform.zoom)

      // Step 3: Draw Edges
      edges.forEach((e) => {
        const source = nodeMap.get(e.source)
        const target = nodeMap.get(e.target)
        if (!source || !target) return

        // Check if edge is in active shortest path
        const isPathEdge =
          pathSet.has(source.id) &&
          pathSet.has(target.id) &&
          Math.abs(pathResult!.path.indexOf(source.id) - pathResult!.path.indexOf(target.id)) === 1

        ctx.beginPath()
        ctx.moveTo(source.x, source.y)
        ctx.lineTo(target.x, target.y)

        if (isPathEdge) {
          ctx.strokeStyle = '#38bdf8'
          ctx.lineWidth = 3
          ctx.shadowColor = '#38bdf8'
          ctx.shadowBlur = 8
        } else {
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)'
          ctx.lineWidth = 1
          ctx.shadowBlur = 0
        }
        ctx.stroke()
        ctx.shadowBlur = 0

        // Draw small directional arrow
        const angle = Math.atan2(target.y - source.y, target.x - source.x)
        const arrowDist = target.radius + 6
        const ax = target.x - Math.cos(angle) * arrowDist
        const ay = target.y - Math.sin(angle) * arrowDist
        const arrowSize = isPathEdge ? 6 : 4

        ctx.beginPath()
        ctx.moveTo(ax, ay)
        ctx.lineTo(ax - Math.cos(angle - 0.45) * arrowSize, ay - Math.sin(angle - 0.45) * arrowSize)
        ctx.lineTo(ax - Math.cos(angle + 0.45) * arrowSize, ay - Math.sin(angle + 0.45) * arrowSize)
        ctx.closePath()
        ctx.fillStyle = isPathEdge ? '#38bdf8' : 'rgba(255, 255, 255, 0.2)'
        ctx.fill()
      })

      // Step 4: Draw Nodes
      nodes.forEach((n) => {
        // Filter visibility check
        const matchesType = typeFilter === 'all' || n.node_type === typeFilter
        const matchesSearch =
          !searchQuery ||
          n.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          n.label.toLowerCase().includes(searchQuery.toLowerCase())

        const isHighlighted = matchesType && matchesSearch
        const isPathNode = pathSet.has(n.id)
        const isSelected = selectedNode?.id === n.id

        ctx.beginPath()
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2)

        // Node fill
        ctx.fillStyle = isPathNode
          ? '#38bdf8'
          : isSelected
            ? '#6366f1'
            : isHighlighted
              ? '#0f1420'
              : 'rgba(15, 20, 32, 0.3)'
        ctx.fill()

        // Node stroke
        ctx.lineWidth = isSelected ? 3 : isPathNode ? 2.5 : 1.5
        ctx.strokeStyle = isPathNode
          ? '#ffffff'
          : isSelected
            ? '#38bdf8'
            : isHighlighted
              ? n.color
              : 'rgba(255, 255, 255, 0.1)'
        if (isPathNode || isSelected) {
          ctx.shadowColor = n.color
          ctx.shadowBlur = 10
        }
        ctx.stroke()
        ctx.shadowBlur = 0

        // Label text
        if (transform.zoom > 0.65 || isPathNode || isSelected) {
          ctx.font = `${isPathNode || isSelected ? 'bold 11px' : '10px'} "JetBrains Mono", monospace`
          ctx.fillStyle = isPathNode
            ? '#ffffff'
            : isSelected
              ? '#38bdf8'
              : isHighlighted
                ? '#cbd5e1'
                : 'rgba(148, 163, 184, 0.3)'
          ctx.textAlign = 'center'
          ctx.fillText(n.label || n.id, n.x, n.y + n.radius + 12)
        }
      })

      ctx.restore()
      animationFrameId = requestAnimationFrame(render)
    }

    render()

    return () => {
      cancelAnimationFrame(animationFrameId)
    }
  }, [typeFilter, searchQuery, pathResult, selectedNode])

  // 4. Mouse / Touch Pan and Zoom Handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const mouseY = e.clientY - rect.top

    // Convert mouse to world coordinates
    const worldX = (mouseX - transformRef.current.x) / transformRef.current.zoom
    const worldY = (mouseY - transformRef.current.y) / transformRef.current.zoom

    // Check if clicked a node
    const clicked = nodesRef.current.find((n) => Math.hypot(n.x - worldX, n.y - worldY) <= n.radius + 6)
    if (clicked) {
      draggedNodeRef.current = clicked
      setSelectedNode(clicked)
    } else {
      isDraggingRef.current = true
      dragStartRef.current = { x: mouseX - transformRef.current.x, y: mouseY - transformRef.current.y }
    }
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const mouseY = e.clientY - rect.top

    if (draggedNodeRef.current) {
      draggedNodeRef.current.x = (mouseX - transformRef.current.x) / transformRef.current.zoom
      draggedNodeRef.current.y = (mouseY - transformRef.current.y) / transformRef.current.zoom
      draggedNodeRef.current.vx = 0
      draggedNodeRef.current.vy = 0
    } else if (isDraggingRef.current) {
      transformRef.current.x = mouseX - dragStartRef.current.x
      transformRef.current.y = mouseY - dragStartRef.current.y
    }
  }

  const handleMouseUp = () => {
    isDraggingRef.current = false
    draggedNodeRef.current = null
  }

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92
    const newZoom = Math.min(3.0, Math.max(0.35, transformRef.current.zoom * zoomFactor))
    transformRef.current.zoom = newZoom
  }

  const resetView = () => {
    transformRef.current = { x: 0, y: 0, zoom: 1 }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', paddingBottom: '4rem' }}>
      {/* Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
          <Badge variant="purple" size="sm">PARADIGM 2: TOPOLOGY VISUALIZER</Badge>
          <span className="mono text-muted" style={{ fontSize: 'var(--text-xs)' }}>
            Force-Directed NetworkX Canvas
          </span>
        </div>
        <h1 style={{ fontSize: 'var(--text-3xl)' }}>Interactive Graph Topology & Path Traversal</h1>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
          Explore directional relationships, pan & zoom through the knowledge graph, and compute live shortest paths.
        </p>
      </div>

      {/* Metrics Row */}
      {topology && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
          <StatCard
            label="Total Nodes"
            value={topology.node_count}
            subtitle={`${Object.keys(topology.node_types).length} entity categories`}
            badge={<Badge variant="purple" size="sm">V</Badge>}
            accentColor="var(--engine-graph)"
          />
          <StatCard
            label="Directional Edges"
            value={topology.edge_count}
            subtitle="Adjacency traversals"
            badge={<Badge variant="indigo" size="sm">E</Badge>}
            accentColor="var(--accent-indigo)"
          />
          <StatCard
            label="Active Path"
            value={pathResult?.found ? `${pathResult.length} hops` : '—'}
            subtitle={pathResult?.found ? `${pathResult.path.length} entities traversed` : 'No path active'}
            badge={<Badge variant="cyan" size="sm">PATH</Badge>}
            accentColor="var(--accent-cyan)"
          />
        </div>
      )}

      {loadingTopology && !topology && (
        <div className="tech-panel mono text-muted" style={{ padding: '2rem', textAlign: 'center' }}>
          Loading NetworkX topology from backend...
        </div>
      )}

      {topologyError && (
        <ErrorState message={topologyError} onRetry={fetchTopology} isRetrying={loadingTopology} />
      )}

      {/* Interactive Graph Canvas & Controls Panel */}
      <section
        className="tech-panel tech-corner-marks graph-workbench-layout"
        style={{
          background: 'var(--bg-surface-elevated)',
          borderRadius: 'var(--radius-md)',
          overflow: 'hidden',
          minHeight: '620px',
        }}
      >
        {/* Main Canvas Area */}
        <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', height: '100%', minHeight: '520px' }}>
          {/* Top Bar on Canvas: Search & Filters */}
          <div
            style={{
              position: 'absolute',
              top: '12px',
              left: '12px',
              right: '12px',
              zIndex: 10,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.6rem',
              pointerEvents: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', pointerEvents: 'auto', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="Search node ID or label..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '210px',
                  padding: '0.35rem 0.65rem',
                  fontSize: '11.5px',
                  background: 'var(--bg-glass-elevated)',
                  backdropFilter: 'blur(12px)',
                }}
              />

              {/* Type Filter Buttons */}
              <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                {['all', 'participant', 'team', 'project', 'college'].map((t) => (
                  <button
                    key={t}
                    onClick={() => setTypeFilter(t)}
                    className="mono"
                    style={{
                      fontSize: '10.5px',
                      padding: '0.25rem 0.5rem',
                      borderRadius: 'var(--radius-xs)',
                      background: typeFilter === t ? 'rgba(56, 189, 248, 0.15)' : 'rgba(0, 0, 0, 0.65)',
                      color: typeFilter === t ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                      border: `1px solid ${typeFilter === t ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`,
                      cursor: 'pointer',
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ pointerEvents: 'auto' }}>
              <button
                onClick={resetView}
                className="mono"
                style={{
                  fontSize: '10.5px',
                  padding: '0.35rem 0.65rem',
                  borderRadius: 'var(--radius-xs)',
                  background: 'var(--bg-glass-elevated)',
                  border: '1px solid var(--border-medium)',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                }}
              >
                Reset View
              </button>
            </div>
          </div>

          {/* Graph Canvas */}
          <canvas
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onWheel={handleWheel}
            style={{
              width: '100%',
              height: '100%',
              display: 'block',
              cursor: isDraggingRef.current ? 'grabbing' : 'grab',
              background: 'radial-gradient(circle at 50% 50%, rgba(16, 20, 32, 0.8) 0%, rgba(4, 5, 7, 0.95) 100%)',
            }}
          />

          {/* Canvas Bottom Legend */}
          <div
            style={{
              position: 'absolute',
              bottom: '10px',
              left: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              pointerEvents: 'none',
              fontSize: '10.5px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <span>Drag to pan · Scroll to zoom · Click node to inspect</span>
          </div>
        </div>

        {/* Right Side: Shortest Path & Node Inspector Sidebar */}
        <div
          style={{
            borderLeft: '1px solid var(--border-subtle)',
            background: 'var(--bg-surface)',
            padding: '1.2rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.2rem',
            overflowY: 'auto',
          }}
        >
          {/* Path Finder Section */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="mono text-cyan" style={{ fontSize: '11px', fontWeight: 600 }}>
                SHORTEST PATH TRAVERSAL
              </span>
              <Badge variant="purple" size="sm">BFS / Dijkstra</Badge>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              <label className="mono text-muted" style={{ fontSize: '10.5px' }}>SOURCE ENTITY</label>
              <input
                type="text"
                value={sourceNode}
                onChange={(e) => setSourceNode(e.target.value)}
                style={{ fontSize: '11.5px', padding: '0.35rem 0.6rem' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              <label className="mono text-muted" style={{ fontSize: '10.5px' }}>TARGET ENTITY</label>
              <input
                type="text"
                value={targetNode}
                onChange={(e) => setTargetNode(e.target.value)}
                style={{ fontSize: '11.5px', padding: '0.35rem 0.6rem' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <label className="mono text-secondary" style={{ fontSize: '10.5px', display: 'flex', alignItems: 'center', gap: '0.3rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={directed}
                  onChange={(e) => setDirected(e.target.checked)}
                />
                Directed Only
              </label>

              <Button
                size="sm"
                variant="primary"
                onClick={handleFindPath}
                loading={loadingPath}
              >
                Compute
              </Button>
            </div>

            {/* Quick Presets */}
            <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
              <button
                onClick={() => {
                  setSourceNode('participant:1')
                  setTargetNode('participant:5')
                }}
                className="mono text-dim"
                style={{ fontSize: '10px', background: 'rgba(255, 255, 255, 0.04)', padding: '2px 5px', borderRadius: '2px', border: '1px solid var(--border-subtle)' }}
              >
                participant:1 → 5
              </button>
              <button
                onClick={() => {
                  setSourceNode('college:1')
                  setTargetNode('project:1')
                }}
                className="mono text-dim"
                style={{ fontSize: '10px', background: 'rgba(255, 255, 255, 0.04)', padding: '2px 5px', borderRadius: '2px', border: '1px solid var(--border-subtle)' }}
              >
                college:1 → project:1
              </button>
            </div>

            {/* Path Result Highlight */}
            {pathError && <ErrorState message={pathError} onRetry={handleFindPath} isRetrying={loadingPath} />}

            {pathResult && (
              <div
                className="tech-panel mono"
                style={{
                  padding: '0.8rem',
                  fontSize: '11px',
                  background: 'var(--bg-void)',
                  borderLeft: `3px solid ${pathResult.found ? 'var(--accent-cyan)' : 'var(--status-warning)'}`,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.4rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', color: pathResult.found ? 'var(--accent-cyan)' : 'var(--status-warning)' }}>
                  <span>{pathResult.found ? '✓ PATH DISCOVERED' : 'NO PATH'}</span>
                  <span>{pathResult.length} hops</span>
                </div>

                {pathResult.found && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', marginTop: '0.3rem' }}>
                    {pathResult.path.map((p, idx) => (
                      <div key={p} style={{ color: idx === 0 ? 'var(--text-primary)' : idx === pathResult.path.length - 1 ? 'var(--accent-cyan)' : 'var(--text-secondary)' }}>
                        {idx + 1}. {p}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Node Inspector Section */}
          <div
            style={{
              borderTop: '1px solid var(--border-subtle)',
              paddingTop: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.6rem',
            }}
          >
            <span className="mono text-muted" style={{ fontSize: '11px', textTransform: 'uppercase' }}>
              NODE INSPECTOR
            </span>

            {selectedNode ? (
              <div
                className="tech-panel mono"
                style={{
                  padding: '0.8rem',
                  background: 'var(--bg-void)',
                  fontSize: '11px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.4rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{selectedNode.id}</span>
                  <Badge variant="purple" size="sm">{selectedNode.node_type}</Badge>
                </div>
                <div style={{ color: 'var(--text-secondary)' }}>{selectedNode.label}</div>

                {Object.keys(selectedNode.attributes).length > 0 && (
                  <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '0.4rem', marginTop: '0.2rem' }}>
                    <div className="text-dim" style={{ fontSize: '10px' }}>ATTRIBUTES:</div>
                    {Object.entries(selectedNode.attributes).map(([k, v]) => (
                      <div key={k} style={{ color: 'var(--text-dim)', fontSize: '10px' }}>
                        {k}: <span style={{ color: 'var(--text-secondary)' }}>{String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ display: 'flex', gap: '0.3rem', marginTop: '0.4rem' }}>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setSourceNode(selectedNode.id)}
                  >
                    Set as Source
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setTargetNode(selectedNode.id)}
                  >
                    Set as Target
                  </Button>
                </div>
              </div>
            ) : (
              <div className="mono text-dim" style={{ fontSize: '11px' }}>
                Click any node on the graph canvas to inspect attributes and connections.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
