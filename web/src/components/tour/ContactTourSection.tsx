import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { easeOut } from '../../motion/variants'
import { EditorialTourPanel } from './EditorialTourPanel'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

const fade = { duration: 0.38, ease: easeOut }

type Props = {
  reduceMotion: boolean | null
  advance: () => void
  rewind: () => void
}

export function ContactTourSection({ reduceMotion, advance, rewind }: Props) {
  const enter = reduceMotion ? false : { opacity: 0, y: 14 }
  const transition = reduceMotion ? { duration: 0 } : fade
  const [healthJson, setHealthJson] = useState<string | null>(null)
  const [healthErr, setHealthErr] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}/api/health`)
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status))
        return r.json()
      })
      .then((d) => {
        if (!cancelled) {
          setHealthJson(JSON.stringify(d, null, 2))
          setHealthErr(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHealthJson(null)
          setHealthErr(true)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section className="tour-section-shell tour-section--editorial">
      <div className="tour-single-stack">
        <motion.div
          key="contact-copy"
          className="tour-panel-scroll"
          initial={enter}
          animate={{ opacity: 1, y: 0 }}
          transition={transition}
        >
          <EditorialTourPanel
            advance={advance}
            rewind={rewind}
            wheelHint="휠 ↓ 첫 화면으로 돌아가기, ↑ 이전"
          >
            <p className="hero-panel-eyebrow">Contact</p>
            <h2 className="hero-panel-headline">
              Class Orbit
              <br />
              shell.
            </h2>
            <p className="hero-panel-lead">
              <span className="hero-panel-accent" lang="en">
                Contact, API status, one surface.
              </span>{' '}
              「정식 서비스에서는 이 화면에서 연락처와 서비스 상태를 바로 확인할 수 있습니다.」
              <br />
              <br />
              {healthJson ? (
                <pre className="tour-health-pre" role="status" aria-label="API health JSON">
                  {healthJson}
                </pre>
              ) : healthErr ? (
                <p className="tour-health-fallback">
                  백엔드가 꺼져 있거나 프록시가 없으면 /api/health를 불러올 수 없습니다. 로컬에서는 Vite와
                  uvicorn을 함께 띄운 뒤 새로고침하세요.
                </p>
              ) : (
                <p className="tour-health-fallback">API 상태를 불러오는 중…</p>
              )}
              <br />
              2026 — Educational AI interface shell
            </p>
          </EditorialTourPanel>
        </motion.div>
      </div>
    </section>
  )
}
