import React, { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'

/**
 * Custom GLSL Vertex Shader
 * Synthesizes three computational paradigms into procedural geometric wave fields:
 * - Relational: Quantized Cartesian stepping (structured tabular rows & columns)
 * - Graph: Radial harmonic branching waves (topological adjacency)
 * - Vector: Continuous high-dimensional cosine interference lobes (semantic distance)
 * - Unified: Convergence into consensus elevation
 */
const VERTEX_SHADER = `
  uniform float uTime;
  uniform vec2 uMouse;
  uniform float uReducedMotion;
  uniform float uStage; // 0.0: Overview, 1.0: Relational, 2.0: Graph, 3.0: Vector, 4.0: Unified

  varying vec2 vUv;
  varying float vElevation;
  varying vec3 vNormalVec;

  // Pseudo-random & simplex-like harmonic noise
  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
  }

  void main() {
    vUv = uv;

    vec3 pos = position;
    float t = uTime * (uReducedMotion > 0.5 ? 0.05 : 0.45);

    // 1. Relational Structured Stepping (Quantized grid predicates)
    float gridStep = floor(pos.x * 2.5) / 2.5 + floor(pos.y * 2.5) / 2.5;
    float relationalWave = sin(gridStep * 3.1415 + t * 0.5) * 0.22;

    // 2. Graph Radial Branching (Network topology adjacency)
    float distFromCenter = length(pos.xy - uMouse * 0.4);
    float graphWave = sin(distFromCenter * 5.5 - t * 1.2) * cos(atan(pos.y, pos.x) * 4.0) * 0.35;

    // 3. Vector High-Dimensional Cosine Lobe Interference (Semantic proximity)
    float vectorWave = (
      sin(pos.x * 2.8 + t * 0.7) * cos(pos.y * 2.4 - t * 0.5) +
      sin((pos.x + pos.y) * 3.2 + t * 0.9) * 0.5
    ) * 0.38;

    // 4. Multi-Paradigm Dynamic Convergence
    // Modulate weights smoothly based on stage & mouse proximity
    float mouseInfluence = smoothstep(1.8, 0.0, distFromCenter) * 0.3;
    float elevation = (relationalWave * 0.35 + graphWave * 0.4 + vectorWave * 0.45) + mouseInfluence;

    // Attenuate peak displacement in the upper-left quadrant to preserve crisp typography readability
    float textZoneDamping = clamp(0.55 + 0.45 * smoothstep(0.0, 1.8, length(pos.xy - vec2(-1.2, 0.4))), 0.55, 1.0);
    elevation *= textZoneDamping;

    pos.z += elevation * (uReducedMotion > 0.5 ? 0.3 : 1.0);

    vElevation = pos.z;
    vNormalVec = normal;

    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`

/**
 * Custom GLSL Fragment Shader
 * Renders obsidian base, spectral cyan, deep indigo, and fine CAD coordinate lines
 */
const FRAGMENT_SHADER = `
  uniform float uTime;
  uniform vec2 uResolution;
  uniform float uReducedMotion;

  varying vec2 vUv;
  varying float vElevation;
  varying vec3 vNormalVec;

  void main() {
    // Technical CAD grid lines
    vec2 grid = abs(fract(vUv * 36.0 - 0.5) - 0.5) / fwidth(vUv * 36.0);
    float line = min(grid.x, grid.y);
    float gridAlpha = 1.0 - min(line, 1.0);

    // Color Palette: Obsidian (#040507), Spectral Cyan (#38bdf8), Indigo (#6366f1), Emerald (#10b981)
    vec3 colorObsidian = vec3(0.024, 0.031, 0.047); // #06080c
    vec3 colorCyan     = vec3(0.22, 0.74, 0.97);     // #38bdf8
    vec3 colorIndigo   = vec3(0.39, 0.40, 0.94);     // #6366f1
    vec3 colorEmerald  = vec3(0.06, 0.72, 0.50);     // #10b981

    // Elevation gradient mapping
    float normElevation = clamp((vElevation + 0.4) / 0.8, 0.0, 1.0);
    vec3 fieldColor = mix(colorObsidian, colorIndigo, smoothstep(0.0, 0.45, normElevation));
    fieldColor = mix(fieldColor, colorCyan, smoothstep(0.45, 0.85, normElevation));
    fieldColor = mix(fieldColor, colorEmerald, smoothstep(0.85, 1.0, normElevation) * 0.3);

    // Blend grid lines with glowing highlights
    vec3 finalColor = fieldColor + vec3(0.22, 0.74, 0.97) * (gridAlpha * 0.08);

    // Radial vignette attenuation to preserve maximum foreground readability
    vec2 centerUv = vUv - 0.5;
    float vignette = 1.0 - dot(centerUv, centerUv) * 1.45;
    vignette = clamp(vignette, 0.0, 1.0);

    gl_FragColor = vec4(finalColor * vignette, 0.70);
  }
`

interface ShaderBackgroundProps {
  stage?: number // 0: Overview, 1: Relational, 2: Graph, 3: Vector, 4: Unified
}

export const ShaderBackground: React.FC<ShaderBackgroundProps> = ({ stage = 0 }) => {
  const mountRef = useRef<HTMLDivElement | null>(null)
  const [webGLSupported, setWebGLSupported] = useState<boolean>(true)

  useEffect(() => {
    const container = mountRef.current
    if (!container) return

    // 1. Check WebGL support
    let isSupported = false
    try {
      const testCanvas = document.createElement('canvas')
      isSupported = !!(window.WebGLRenderingContext && (testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl')))
    } catch {
      isSupported = false
    }

    if (!isSupported) {
      setWebGLSupported(false)
      return
    }

    // 2. Setup Three.js Scene, Camera, Renderer
    let width = container.clientWidth || window.innerWidth
    let height = container.clientHeight || window.innerHeight

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100)
    camera.position.set(0, -1.8, 2.6)
    camera.lookAt(0, 0, 0)

    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance',
      })
    } catch {
      setWebGLSupported(false)
      return
    }

    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x040507, 0)
    container.appendChild(renderer.domElement)

    // 3. Create Custom Procedural Mesh with ShaderMaterial
    const geometry = new THREE.PlaneGeometry(6.5, 4.5, 96, 72)

    const uniforms = {
      uTime: { value: 0.0 },
      uMouse: { value: new THREE.Vector2(0, 0) },
      uResolution: { value: new THREE.Vector2(width, height) },
      uReducedMotion: { value: 0.0 },
      uStage: { value: stage },
    }

    // Check prefers-reduced-motion
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    uniforms.uReducedMotion.value = mediaQuery.matches ? 1.0 : 0.0

    const handleMediaChange = (e: MediaQueryListEvent) => {
      uniforms.uReducedMotion.value = e.matches ? 1.0 : 0.0
    }
    mediaQuery.addEventListener('change', handleMediaChange)

    const material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms,
      transparent: true,
      wireframe: false,
      depthWrite: false,
    })

    const mesh = new THREE.Mesh(geometry, material)
    mesh.rotation.x = -Math.PI * 0.22
    scene.add(mesh)

    // Optional ambient particles for depth
    const particleCount = 180
    const particleGeometry = new THREE.BufferGeometry()
    const positions = new Float32Array(particleCount * 3)
    for (let i = 0; i < particleCount * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 6
      positions[i + 1] = (Math.random() - 0.5) * 4
      positions[i + 2] = (Math.random() - 0.5) * 1.5
    }
    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const particleMaterial = new THREE.PointsMaterial({
      color: 0x38bdf8,
      size: 0.025,
      transparent: true,
      opacity: 0.35,
      blending: THREE.AdditiveBlending,
    })
    const particlePoints = new THREE.Points(particleGeometry, particleMaterial)
    scene.add(particlePoints)

    // 4. Mouse interaction smoothing
    let targetMouseX = 0
    let targetMouseY = 0

    const handleMouseMove = (e: MouseEvent) => {
      targetMouseX = (e.clientX / window.innerWidth) * 2 - 1
      targetMouseY = -(e.clientY / window.innerHeight) * 2 + 1
    }
    window.addEventListener('mousemove', handleMouseMove, { passive: true })

    // 5. Handle Resize
    const handleResize = () => {
      if (!container || !renderer) return
      width = container.clientWidth || window.innerWidth
      height = container.clientHeight || window.innerHeight
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      renderer.setSize(width, height)
      uniforms.uResolution.value.set(width, height)
    }
    window.addEventListener('resize', handleResize)

    // 6. Visibility handling (pause rendering when tab is hidden)
    let isVisible = true
    const handleVisibilityChange = () => {
      isVisible = !document.hidden
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)

    // 7. Render Animation Loop
    let animationFrameId: number
    const clock = new THREE.Clock()

    const animate = () => {
      if (isVisible) {
        const elapsedTime = clock.getElapsedTime()

        uniforms.uTime.value = elapsedTime

        // Smooth mouse interpolation
        uniforms.uMouse.value.x += (targetMouseX - uniforms.uMouse.value.x) * 0.04
        uniforms.uMouse.value.y += (targetMouseY - uniforms.uMouse.value.y) * 0.04

        // Subtle camera orbit reaction
        camera.position.x = uniforms.uMouse.value.x * 0.15
        camera.position.y = -1.8 + uniforms.uMouse.value.y * 0.1
        camera.lookAt(0, 0, 0)

        // Slow particle drift
        particlePoints.rotation.y = elapsedTime * 0.03

        renderer.render(scene, camera)
      }

      animationFrameId = requestAnimationFrame(animate)
    }

    animate()

    // 8. Disposal Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId)
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('resize', handleResize)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      mediaQuery.removeEventListener('change', handleMediaChange)

      geometry.dispose()
      material.dispose()
      particleGeometry.dispose()
      particleMaterial.dispose()
      renderer.dispose()

      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [stage])

  // Canvas 2D Fallback for environments lacking WebGL
  if (!webGLSupported) {
    return (
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          pointerEvents: 'none',
          zIndex: 0,
          background: 'radial-gradient(circle at 50% 30%, rgba(56, 189, 248, 0.06) 0%, rgba(4, 5, 7, 0.95) 75%)',
        }}
      />
    )
  }

  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 0,
        overflow: 'hidden',
      }}
    >
      <div
        ref={mountRef}
        style={{
          width: '100%',
          height: '100%',
          display: 'block',
        }}
      />
      {/* Editorial Directional Scrim & Vignette Overlay */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background:
            'linear-gradient(90deg, rgba(4, 5, 7, 0.85) 0%, rgba(4, 5, 7, 0.62) 38%, rgba(4, 5, 7, 0.20) 68%, transparent 100%), radial-gradient(circle at 25% 35%, rgba(4, 5, 7, 0.50) 0%, transparent 70%), radial-gradient(circle at 75% 35%, transparent 32%, rgba(4, 5, 7, 0.85) 100%)',
          pointerEvents: 'none',
        }}
      />
    </div>
  )
}
