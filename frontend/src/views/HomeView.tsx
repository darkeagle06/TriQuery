import React, { useEffect, useRef, useState } from 'react'
import type { HealthResponse } from '../types/api'
import { Badge } from '../components/common/Badge'
import { Button } from '../components/common/Button'
import type { NavigationDestination } from '../components/layout/Header'

interface HomeViewProps {
  health: HealthResponse | null
  onNavigate: (dest: NavigationDestination) => void
}

type NarrativeStage = 'hero' | 'relational' | 'graph' | 'vector' | 'unified'

export const HomeView: React.FC<HomeViewProps> = ({ health, onNavigate }) => {
  const [activeStage, setActiveStage] = useState<NarrativeStage>('hero')

  // Section observer for scroll synchronization
  const stageRefs = {
    hero: useRef<HTMLDivElement | null>(null),
    relational: useRef<HTMLDivElement | null>(null),
    graph: useRef<HTMLDivElement | null>(null),
    vector: useRef<HTMLDivElement | null>(null),
    unified: useRef<HTMLDivElement | null>(null),
  }

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const id = entry.target.getAttribute('data-stage') as NarrativeStage
            if (id) setActiveStage(id)
          }
        }
      },
      { threshold: 0.35, rootMargin: '-80px 0px -40% 0px' }
    )

    Object.values(stageRefs).forEach((ref) => {
      if (ref.current) observer.observe(ref.current)
    })

    return () => observer.disconnect()
  }, [])

  const scrollToStage = (stage: NarrativeStage) => {
    const ref = stageRefs[stage]
    if (ref.current) {
      ref.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return (
    <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: '5rem', paddingBottom: '6rem' }}>
      {/* Sticky Stage Navigation Rail */}
      <nav
        aria-label="Story stages"
        style={{
          position: 'sticky',
          top: '75px',
          zIndex: 30,
          display: 'flex',
          justifyContent: 'center',
          pointerEvents: 'none',
        }}
      >
        <div
          className="tech-panel"
          style={{
            pointerEvents: 'auto',
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            padding: '0.35rem 0.6rem',
            background: 'var(--bg-glass-elevated)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-full)',
            boxShadow: 'var(--shadow-medium)',
          }}
        >
          <span className="mono text-dim" style={{ fontSize: '10px', paddingLeft: '0.4rem', paddingRight: '0.2rem' }}>
            NARRATIVE:
          </span>

          {[
            { id: 'hero', label: 'Overview' },
            { id: 'relational', label: '1. Relational SQL', color: 'var(--engine-relational)' },
            { id: 'graph', label: '2. Graph Traversal', color: 'var(--engine-graph)' },
            { id: 'vector', label: '3. Vector Space', color: 'var(--engine-vector)' },
            { id: 'unified', label: '4. Unified RRF', color: 'var(--engine-fusion)' },
          ].map((st) => {
            const isActive = activeStage === st.id
            return (
              <button
                key={st.id}
                onClick={() => scrollToStage(st.id as NarrativeStage)}
                className="mono"
                style={{
                  fontSize: '11px',
                  fontWeight: isActive ? 600 : 400,
                  padding: '0.25rem 0.65rem',
                  borderRadius: 'var(--radius-full)',
                  background: isActive ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
                  color: isActive ? (st.color || 'var(--text-primary)') : 'var(--text-secondary)',
                  border: `1px solid ${isActive ? (st.color || 'var(--accent-cyan)') : 'transparent'}`,
                  transition: 'var(--transition-fast)',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {st.label}
              </button>
            )
          })}
        </div>
      </nav>

      {/* =====================================================================
       * Opening Hero: The Convergence Problem
       * ===================================================================== */}
      <section
        ref={stageRefs.hero}
        data-stage="hero"
        style={{
          minHeight: '75vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: '2rem',
          maxWidth: '920px',
          paddingTop: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', flexWrap: 'wrap' }}>
          <Badge variant="cyan" dot size="sm">
            ARCHITECTURE VERIFIED · MYSQL 8.X BACKEND
          </Badge>
          <span className="mono text-muted" style={{ fontSize: 'var(--text-xs)' }}>
            {health?.table_counts ? `${Object.values(health.table_counts).reduce((a, b) => a + b, 0)} records · ${health.graph.node_count} nodes · ${health.vector.document_count} docs` : 'Engine online'}
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h1
            style={{
              fontSize: 'clamp(2.6rem, 5.8vw, 4.2rem)',
              fontWeight: 800,
              lineHeight: 1.08,
              letterSpacing: '-0.04em',
              color: '#ffffff',
              textShadow: '0 2px 24px rgba(4, 5, 7, 0.95), 0 0 45px rgba(4, 5, 7, 0.8)',
            }}
          >
            The Convergence Problem in Multi-Paradigm Data
          </h1>

          <p
            style={{
              fontSize: 'var(--text-xl)',
              color: 'var(--text-secondary)',
              lineHeight: 1.55,
              maxWidth: '780px',
              textShadow: '0 1px 16px rgba(4, 5, 7, 0.9)',
            }}
          >
            Real-world systems demand structured relational predicates, deep topological graph traversals,
            and unstructured semantic similarity. Yet forcing them into a single monolithic store produces
            severe impedance mismatches.
          </p>

          <p
            style={{
              fontSize: 'var(--text-base)',
              color: 'var(--text-muted)',
              lineHeight: 1.6,
              maxWidth: '720px',
              textShadow: '0 1px 12px rgba(4, 5, 7, 0.9)',
            }}
          >
            <strong style={{ color: 'var(--accent-cyan)' }}>TriQuery</strong> unifies three native query engines
            through an explainable execution planner and consensus ranking powered by{' '}
            <span style={{ color: 'var(--engine-fusion)', fontWeight: 600 }}>Reciprocal Rank Fusion (RRF)</span>.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
          <Button
            size="lg"
            variant="primary"
            onClick={() => onNavigate('studio')}
            icon={<span className="mono">▶</span>}
          >
            Launch Query Studio
          </Button>

          <Button
            size="lg"
            variant="secondary"
            onClick={() => scrollToStage('relational')}
          >
            Explore 4-Stage Narrative ↓
          </Button>
        </div>
      </section>

      {/* =====================================================================
       * Stage 1: Relational Computation (SQL)
       * ===================================================================== */}
      <section
        ref={stageRefs.relational}
        data-stage="relational"
        className="tech-panel tech-corner-marks"
        style={{
          padding: '2.5rem',
          background: 'var(--bg-surface-elevated)',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 310px), 1fr))',
          gap: '2.5rem',
          alignItems: 'center',
          borderLeft: '4px solid var(--engine-relational)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Badge variant="cyan" size="sm">STAGE 1</Badge>
            <span className="mono text-cyan" style={{ fontSize: 'var(--text-xs)', fontWeight: 600 }}>
              PARADIGM 1: RELATIONAL SQL ENGINE
            </span>
          </div>

          <h2 style={{ fontSize: 'var(--text-2xl)', color: 'var(--text-primary)' }}>
            Deterministic Predicates & Normalized Constraints
          </h2>

          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.65 }}>
            Relational SQL enforces mandatory hard filters that no probabilistic model can replicate with 100% guarantee.
            Foreign keys between <span className="mono text-cyan">colleges</span>, <span className="mono text-cyan">hackathons</span>,{' '}
            <span className="mono text-cyan">teams</span>, and <span className="mono text-cyan">projects</span> ensure ACID referential integrity.
          </p>

          <div
            className="mono"
            style={{
              padding: '0.8rem 1rem',
              background: 'var(--bg-void)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '11.5px',
              color: 'var(--text-secondary)',
              lineHeight: 1.6,
            }}
          >
            <div style={{ color: 'var(--text-dim)' }}>-- Parameterized Relational Predicate Execution</div>
            <div>SELECT p.project_id, p.project_title, c.college_name</div>
            <div>FROM projects p</div>
            <div>JOIN teams t ON p.team_id = t.team_id</div>
            <div>JOIN colleges c ON t.college_id = c.college_id</div>
            <div style={{ color: 'var(--accent-cyan)' }}>WHERE p.track = 'Robotics & AI'</div>
            <div style={{ color: 'var(--text-dim)' }}>-- Evaluated via B-Tree Index: O(log N)</div>
          </div>

          <div style={{ display: 'flex', gap: '0.8rem' }}>
            <Button variant="secondary" size="sm" onClick={() => onNavigate('relational')}>
              Inspect MySQL Tables & Schema →
            </Button>
          </div>
        </div>

        {/* Live Relational Data Representation */}
        <div
          style={{
            padding: '1.4rem',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="mono text-muted" style={{ fontSize: '11px' }}>
              ACTUAL SEED DATA: 7 NORMALIZED TABLES
            </span>
            <Badge variant="cyan" size="sm">InnoDB ACID</Badge>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {[
              { tbl: 'colleges', rows: 5, desc: 'Academic institutions (IIT Delhi, IIT Bombay...)' },
              { tbl: 'hackathons', rows: 3, desc: 'National competitions (HackAI, DevClash...)' },
              { tbl: 'teams', rows: 6, desc: 'Competing student collectives' },
              { tbl: 'participants', rows: 12, desc: 'Developers & researchers' },
              { tbl: 'projects', rows: 6, desc: 'Hardware & software submissions' },
              { tbl: 'awards', rows: 6, desc: 'Grand prizes & monetary awards' },
            ].map((item) => (
              <div
                key={item.tbl}
                className="tech-panel mono"
                style={{
                  padding: '0.45rem 0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '11px',
                  background: 'rgba(0, 0, 0, 0.25)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{item.tbl}</span>
                  <span className="text-dim">({item.desc})</span>
                </div>
                <span className="text-cyan">{item.rows} rows</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* =====================================================================
       * Stage 2: Graph Computation (NetworkX)
       * ===================================================================== */}
      <section
        ref={stageRefs.graph}
        data-stage="graph"
        className="tech-panel tech-corner-marks"
        style={{
          padding: '2.5rem',
          background: 'var(--bg-surface-elevated)',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 310px), 1fr))',
          gap: '2.5rem',
          alignItems: 'center',
          borderLeft: '4px solid var(--engine-graph)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Badge variant="purple" size="sm">STAGE 2</Badge>
            <span className="mono text-purple" style={{ fontSize: 'var(--text-xs)', fontWeight: 600 }}>
              PARADIGM 2: NETWORKX GRAPH TOPOLOGY
            </span>
          </div>

          <h2 style={{ fontSize: 'var(--text-2xl)', color: 'var(--text-primary)' }}>
            Traversing Collaborator Networks & Lineage
          </h2>

          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.65 }}>
            Answering queries like <em>"Find projects developed by teammates of alumni affiliated with IIT Delhi"</em> in SQL
            requires 5-table recursive self-joins with massive Cartesian explosions. In contrast, TriQuery's Graph Engine
            provides <strong>index-free adjacency</strong> in linear $O(V + E)$ time.
          </p>

          <div
            className="mono"
            style={{
              padding: '0.8rem 1rem',
              background: 'var(--bg-void)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '11.5px',
              color: 'var(--text-secondary)',
              lineHeight: 1.6,
            }}
          >
            <div style={{ color: 'var(--text-dim)' }}>-- Shortest Path Traversal (BFS / Dijkstra)</div>
            <div>participant:1 (Aarav Sharma)</div>
            <div className="text-purple">  └─[ MEMBER_OF ]→ team:1 (NeuralVanguard)</div>
            <div className="text-cyan">      └─[ SUBMITTED ]→ project:1 (AeroVision)</div>
            <div className="text-indigo">          └─[ WON_AWARD ]→ award:1 (Grand Winner)</div>
            <div style={{ color: 'var(--text-dim)' }}>-- Traversal Complexity: O(V + E) ~ 0.22 ms</div>
          </div>

          <div style={{ display: 'flex', gap: '0.8rem' }}>
            <Button variant="secondary" size="sm" onClick={() => onNavigate('graph')}>
              Open Interactive Graph Explorer →
            </Button>
          </div>
        </div>

        {/* Live Graph Topology Representation */}
        <div
          style={{
            padding: '1.4rem',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="mono text-muted" style={{ fontSize: '11px' }}>
              NETWORK TOPOLOGY: 38 NODES · 55 EDGES
            </span>
            <Badge variant="purple" size="sm">DiGraph</Badge>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem' }}>
            {[
              { type: 'participant', count: 12, edge: 'MEMBER_OF' },
              { type: 'team', count: 6, edge: 'SUBMITTED' },
              { type: 'college', count: 5, edge: 'AFFILIATED_WITH' },
              { type: 'project', count: 6, edge: 'WON_AWARD' },
              { type: 'hackathon', count: 3, edge: 'HOSTED_AT' },
              { type: 'award', count: 6, edge: 'RECEIVED' },
            ].map((n) => (
              <div
                key={n.type}
                className="tech-panel mono"
                style={{
                  padding: '0.6rem 0.8rem',
                  fontSize: '11px',
                  background: 'rgba(0, 0, 0, 0.25)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.2rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{n.type}</span>
                  <span className="text-purple">{n.count}</span>
                </div>
                <span className="text-dim" style={{ fontSize: '10px' }}>Predicate: {n.edge}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* =====================================================================
       * Stage 3: Vector Retrieval (Scikit-Learn TF-IDF)
       * ===================================================================== */}
      <section
        ref={stageRefs.vector}
        data-stage="vector"
        className="tech-panel tech-corner-marks"
        style={{
          padding: '2.5rem',
          background: 'var(--bg-surface-elevated)',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 310px), 1fr))',
          gap: '2.5rem',
          alignItems: 'center',
          borderLeft: '4px solid var(--engine-vector)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Badge variant="emerald" size="sm">STAGE 3</Badge>
            <span className="mono text-emerald" style={{ fontSize: 'var(--text-xs)', fontWeight: 600 }}>
              PARADIGM 3: TF-IDF VECTOR SIMILARITY (COSINE)
            </span>
          </div>

          <h2 style={{ fontSize: 'var(--text-2xl)', color: 'var(--text-primary)' }}>
            High-Dimensional Lexical Proximity
          </h2>

          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.65 }}>
            Keyword searching and SQL <span className="mono">LIKE '%drone%'</span> fail when users query conceptual terms
            like <em>"autonomous visual SLAM pathfinding in GPS-denied zones"</em>. The Vector Engine vectorizes project summaries
            and technical stacks using term frequency-inverse document frequency (TF-IDF) into an $L_2$-normalized sparse vector space, measuring similarity through the cosine angle.
          </p>

          <div
            style={{
              padding: '0.8rem 1rem',
              background: 'rgba(16, 185, 129, 0.06)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '11px',
              color: 'var(--text-secondary)',
              lineHeight: 1.5,
            }}
          >
            <strong style={{ color: 'var(--engine-vector)' }}>Active Provider Specification:</strong><br />
            Configured as <span className="mono text-primary">Scikit-Learn TF-IDF with Cosine Similarity (303 dimensions)</span>.
            Pure Python 3.13 deterministic execution without unneeded external embedding API calls or network latency.
          </div>

          <div style={{ display: 'flex', gap: '0.8rem' }}>
            <Button variant="secondary" size="sm" onClick={() => onNavigate('vector')}>
              Test Vector Similarity Search →
            </Button>
          </div>
        </div>

        {/* Real Vector Match Ranking Preview */}
        <div
          style={{
            padding: '1.4rem',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.8rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="mono text-muted" style={{ fontSize: '11px' }}>
              QUERY: "autonomous drone navigation"
            </span>
            <Badge variant="emerald" size="sm">Top-K = 3</Badge>
          </div>

          {[
            { rank: 1, id: 'project:1', title: 'AeroVision Autonomous Drone Pathfinder', score: 0.241, stack: 'ROS2, OpenCV, PyTorch' },
            { rank: 2, id: 'project:4', title: 'AgriSense Drone Multispectral Yield Analyzer', score: 0.165, stack: 'Python, GDAL, YOLOv8' },
            { rank: 3, id: 'project:3', title: 'TransitPulse Real-Time Traffic AI', score: 0.089, stack: 'Kafka, PyTorch, FastAPI' },
          ].map((v) => (
            <div
              key={v.id}
              className="tech-panel mono"
              style={{
                padding: '0.75rem',
                fontSize: '11px',
                background: 'rgba(0, 0, 0, 0.25)',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.35rem',
                borderLeft: `2px solid var(--engine-vector)`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>#{v.rank} {v.title}</span>
                <span className="text-emerald">{v.score.toFixed(3)}</span>
              </div>
              <div className="text-dim" style={{ fontSize: '10px' }}>{v.id} · Stack: {v.stack}</div>
            </div>
          ))}
        </div>
      </section>

      {/* =====================================================================
       * Stage 4: Unified Ranking (Reciprocal Rank Fusion)
       * ===================================================================== */}
      <section
        ref={stageRefs.unified}
        data-stage="unified"
        className="tech-panel tech-corner-marks"
        style={{
          padding: '2.5rem',
          background: 'var(--bg-surface-elevated)',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 310px), 1fr))',
          gap: '2.5rem',
          alignItems: 'center',
          borderLeft: '4px solid var(--engine-fusion)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Badge variant="amber" size="sm">STAGE 4</Badge>
            <span className="mono text-amber" style={{ fontSize: 'var(--text-xs)', fontWeight: 600 }}>
              PARADIGM CONVERGENCE: RECIPROCAL RANK FUSION
            </span>
          </div>

          <h2 style={{ fontSize: 'var(--text-2xl)', color: 'var(--text-primary)' }}>
            Consensus Ranking Across Diverse Metric Spaces
          </h2>

          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.65 }}>
            How do you compare a SQL boolean match (1 or 0), a graph path hop count (2 hops),
            and a cosine similarity score (0.241)? <strong>Raw score normalization fails</strong> because these
            distributions have non-comparable variance.
          </p>

          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.65 }}>
            TriQuery maps candidate outputs to their 1-indexed rank position $r_m(d)$ and applies Reciprocal Rank Fusion:
          </p>

          <div
            className="mono"
            style={{
              padding: '0.9rem',
              background: 'var(--bg-void)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '13px',
              color: 'var(--accent-cyan)',
              fontWeight: 600,
              textAlign: 'center',
            }}
          >
            RRF(d) = ∑ [ wₘ / (k + rankₘ(d)) ]  (where k = 60)
          </div>

          <div style={{ display: 'flex', gap: '0.8rem', marginTop: '0.5rem' }}>
            <Button variant="primary" size="lg" onClick={() => onNavigate('studio')}>
              Execute Preset 5 in Query Studio →
            </Button>
          </div>
        </div>

        {/* Fused Consensus Output (Actual Preset 5 Result) */}
        <div
          style={{
            padding: '1.4rem',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="mono text-muted" style={{ fontSize: '11px' }}>
              FUSED CONSENSUS RESULT (PRESET 5)
            </span>
            <Badge variant="amber" size="sm">Consensus Winner</Badge>
          </div>

          <div
            className="tech-panel mono"
            style={{
              padding: '1rem',
              background: 'rgba(245, 158, 11, 0.05)',
              border: '1px solid rgba(245, 158, 11, 0.25)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.6rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-primary)' }}>
                #1 AeroVision Autonomous Drone Pathfinder
              </span>
              <span className="text-amber" style={{ fontWeight: 700 }}>
                RRF: 0.04918
              </span>
            </div>

            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: 0 }}>
              Autonomous visual SLAM and pathfinding for UAVs in GPS-denied disaster environments.
            </p>

            <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginTop: '0.3rem' }}>
              <Badge variant="cyan" size="sm">Relational: Rank #1</Badge>
              <Badge variant="purple" size="sm">Graph: Rank #1</Badge>
              <Badge variant="emerald" size="sm">Vector: Rank #1</Badge>
            </div>

            <div className="text-dim" style={{ fontSize: '10.5px', marginTop: '0.2rem' }}>
              Arithmetic: 1/(60+1) + 1/(60+1) + 1/(60+1) = 3/61 = 0.04918
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
