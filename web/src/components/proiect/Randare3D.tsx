// 3D view of the schematic plan: the plot as a plane, every element as a box at its position, footprint and
// schematic height (inaltime_m) from the same Scene the plan, the sheets and the material list use.
// three.js is loaded on demand; nothing here invents data beyond what the API returned.
import { useEffect, useRef, useState } from 'react'
import { Loader2, RotateCcw } from 'lucide-react'
import type { PlanSchematic } from '@/api/models'
import { Button } from '@/components/ui/button'

const COLORS: Record<string, number> = {
  alee: 0xd9d4c7, skate: 0x9fb7d6, joaca: 0xf2c48d, caini: 0xb9d99b, apa: 0x8cc8e8, pista: 0xc9c2b8, rastel: 0xa7a7a7,
  strat: 0x8fbf6a, magazie: 0xb08a62, compost: 0x7d6a4f, sport: 0xe3a07a, foisor: 0xc79a6b, masa: 0xd7b48a, banca: 0x8d7b68,
  cos: 0x555555, zona: 0xc6d8c0, parcare: 0xb8b8b8, echipament: 0x7fa7c9, iluminat: 0xf0d27a, siguranta: 0xd98c8c,
  semnalizare: 0xe8e0a0, cladire: 0xd6c3a5, verde: 0x9bc98a,
}

export function Randare3D({ plan }: { plan: PlanSchematic }) {
  const host = useRef<HTMLDivElement>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [resetKey, setResetKey] = useState(0)

  useEffect(() => {
    let disposed = false
    let cleanup: (() => void) | undefined
    setState('loading')
    void (async () => {
      try {
        const THREE = await import('three')
        const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js')
        if (disposed || !host.current) return
        const el = host.current
        const w = el.clientWidth || 640
        const h = Math.max(320, Math.round(w * 0.6))
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
        renderer.setSize(w, h)
        renderer.shadowMap.enabled = true
        el.replaceChildren(renderer.domElement)

        const scene = new THREE.Scene()
        scene.background = new THREE.Color(0xf6f7f4)
        const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 2000)
        const span = Math.max(plan.latime_m, plan.lungime_m)
        camera.position.set(plan.latime_m * 0.9, span * 0.9, plan.lungime_m * 1.4)
        const controls = new OrbitControls(camera, renderer.domElement)
        controls.target.set(plan.latime_m / 2, 0, -plan.lungime_m / 2)
        controls.maxPolarAngle = Math.PI / 2 - 0.05
        controls.update()

        scene.add(new THREE.HemisphereLight(0xffffff, 0x8a9a7a, 0.9))
        const sun = new THREE.DirectionalLight(0xffffff, 1.1)
        sun.position.set(span, span * 1.5, span * 0.5)
        sun.castShadow = true
        sun.shadow.mapSize.set(2048, 2048)
        const cam = sun.shadow.camera
        cam.left = -span
        cam.right = span * 2
        cam.top = span * 2
        cam.bottom = -span * 2
        scene.add(sun)

        // Plot (plan y goes "up" on paper = -z in the 3D world so north stays away from the viewer)
        const ground = new THREE.Mesh(
          new THREE.PlaneGeometry(plan.latime_m, plan.lungime_m),
          new THREE.MeshStandardMaterial({ color: 0xdfe9d2 }),
        )
        ground.rotation.x = -Math.PI / 2
        ground.position.set(plan.latime_m / 2, 0, -plan.lungime_m / 2)
        ground.receiveShadow = true
        scene.add(ground)
        const edges = new THREE.LineSegments(
          new THREE.EdgesGeometry(new THREE.PlaneGeometry(plan.latime_m, plan.lungime_m)),
          new THREE.LineBasicMaterial({ color: 0x1f3d1f }),
        )
        edges.rotation.x = -Math.PI / 2
        edges.position.copy(ground.position)
        edges.position.y = 0.01
        scene.add(edges)
        const grid = new THREE.GridHelper(span * 2, Math.round(span * 2 / 5), 0xbfc8b5, 0xe3e8dc)
        grid.position.set(plan.latime_m / 2, -0.01, -plan.lungime_m / 2)
        scene.add(grid)

        for (const e of plan.elemente) {
          const height = Math.max(e.inaltime_m ?? 0, 0.05)
          const geo = new THREE.BoxGeometry(e.latime_m, height, e.lungime_m)
          const mat = new THREE.MeshStandardMaterial({ color: COLORS[e.tip] ?? 0xcccccc, roughness: 0.85 })
          const box = new THREE.Mesh(geo, mat)
          box.position.set(e.x + e.latime_m / 2, height / 2, -(e.y + e.lungime_m / 2))
          box.castShadow = height > 0.1
          box.receiveShadow = true
          scene.add(box)
          const outline = new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: 0x333333 }))
          outline.position.copy(box.position)
          scene.add(outline)
        }

        let frame = 0
        const loop = () => {
          controls.update()
          renderer.render(scene, camera)
          frame = requestAnimationFrame(loop)
        }
        loop()
        const onResize = () => {
          const nw = el.clientWidth || w
          const nh = Math.max(320, Math.round(nw * 0.6))
          renderer.setSize(nw, nh)
          camera.aspect = nw / nh
          camera.updateProjectionMatrix()
        }
        window.addEventListener('resize', onResize)
        setState('ready')
        cleanup = () => {
          cancelAnimationFrame(frame)
          window.removeEventListener('resize', onResize)
          controls.dispose()
          renderer.dispose()
          scene.traverse((o) => {
            const m = o as unknown as { geometry?: { dispose(): void }; material?: { dispose(): void } }
            m.geometry?.dispose?.()
            m.material?.dispose?.()
          })
          el.replaceChildren()
        }
      } catch {
        if (!disposed) setState('error')
      }
    })()
    return () => {
      disposed = true
      cleanup?.()
    }
  }, [plan, resetKey])

  return (
    <div className="space-y-2">
      <div ref={host} className="min-h-80 w-full overflow-hidden rounded-xl border bg-muted/30" aria-label="Randare 3D schematică" />
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>
          {state === 'loading' ? (
            <span className="inline-flex items-center gap-1">
              <Loader2 className="size-3.5 animate-spin" /> se încarcă vederea 3D…
            </span>
          ) : state === 'error' ? (
            'Vederea 3D nu a putut fi pornită în acest browser (WebGL).'
          ) : (
            'Rotește cu mouse-ul, apropie cu rotița. Volumele au înălțimile schematice din specificație; nu sunt produsele reale.'
          )}
        </span>
        <Button variant="ghost" size="sm" onClick={() => setResetKey((k) => k + 1)}>
          <RotateCcw /> Resetează vederea
        </Button>
      </div>
    </div>
  )
}
