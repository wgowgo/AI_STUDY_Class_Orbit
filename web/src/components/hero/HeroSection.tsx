import { motion } from 'framer-motion'
import { easeOut } from '../../motion/variants'

const fade = { duration: 0.38, ease: easeOut }

type Props = {
  tourStep: number
  reduceMotion: boolean | null
  advance: () => void
  rewind: () => void
  onOpenAi: () => void
}

export function HeroSection({
  tourStep,
  reduceMotion,
  advance,
  rewind,
  onOpenAi,
}: Props) {
  const showA = tourStep === 0
  const showB = tourStep === 1

  return (
    <div className="tour-hero-wrap">
      <section
        className="hero hero--viewport hero--content-overlay"
        aria-labelledby={showB ? 'hero-panel-title' : 'hero-title'}
      >
        <div className="tour-hero-stack">
          <motion.div
            className="hero-ui tour-hero-layer"
            aria-hidden={!showA}
            animate={{
              opacity: showA ? 1 : 0,
              visibility: showA ? 'visible' : 'hidden',
              pointerEvents: showA ? 'auto' : 'none',
            }}
            transition={reduceMotion ? { duration: 0 } : fade}
          >
            <motion.p
              className="hero-tagline"
              initial={reduceMotion ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 0.95, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2, ease: easeOut }}
            >
              Made for class. Built for learners.
            </motion.p>

            <div className="hero-title-block">
              <motion.h1
                id="hero-title"
                className="hero-title"
                initial={reduceMotion ? false : { opacity: 0, y: 48 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.75, delay: 0.28, ease: easeOut }}
              >
                <motion.span
                  className="hero-title-sub"
                  initial={reduceMotion ? false : { opacity: 0, letterSpacing: '0.5em' }}
                  animate={{ opacity: 1, letterSpacing: '0.22em' }}
                  transition={{ duration: 0.9, delay: 0.35, ease: easeOut }}
                >
                  CLASS
                </motion.span>
                ORBIT
              </motion.h1>
            </div>

            <motion.div
              className="hero-copy"
              initial={reduceMotion ? false : { opacity: 0, y: 24 }}
              animate={{ opacity: 0.93, y: 0 }}
              transition={{ duration: 0.65, delay: 0.45, ease: easeOut }}
            >
              <p>
                NEIS, 교육통계,  학교 환경 데이터를 바탕으로 수업 품질, 학습
                위험도, 시간표 전략을 하나의 루프로 묶는 교육 AI 프레임워크입니다.
              </p>
            </motion.div>

            {/* Prototype meta box removed */}

            <motion.div
              className="hero-video-card"
              role="figure"
              aria-label="소개 영상 자리"
              initial={reduceMotion ? false : { opacity: 0, scale: 0.92, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.62, ease: easeOut }}
              whileHover={reduceMotion ? undefined : { scale: 1.02 }}
            >
              <div className="hero-video-thumb" />
              <button type="button" className="hero-video-play" onClick={onOpenAi}>
                Play
              </button>
            </motion.div>

            <div className="hero-controls">
              <button type="button" className="hero-control-btn" onClick={advance}>
                다음
              </button>
              <p className="hero-wheel-hint aria-hidden">
                휠 ↓ 또는 ↓ 키
              </p>
            </div>
          </motion.div>

          <motion.div
            className="hero-ui hero-ui--panel tour-hero-layer"
            aria-hidden={!showB}
            animate={{
              opacity: showB ? 1 : 0,
              visibility: showB ? 'visible' : 'hidden',
              pointerEvents: showB ? 'auto' : 'none',
            }}
            transition={reduceMotion ? { duration: 0 } : fade}
          >
            <p className="hero-panel-eyebrow">Intro</p>
            <h2 id="hero-panel-title" className="hero-panel-headline">
              isn’t just
              <br />a dashboard.
            </h2>
            <p className="hero-panel-lead">
              <span className="hero-panel-accent" lang="en">
                Impact over vanity metrics.
              </span>{' '}
              단순한 수치 나열이 아니라, 수업이 학생에게 미칠 영향을 가늠할 수 있는
              기반 데이터를 만든 뒤, 예측, 시뮬레이션으로 이어지는 순환
              구조를 지향합니다.
            </p>
            <div className="hero-controls hero-controls--panel">
              <button
                type="button"
                className="hero-control-btn hero-control-btn--ghost"
                onClick={rewind}
              >
                이전
              </button>
              <button type="button" className="hero-control-btn" onClick={advance}>
                다음
              </button>
              <p className="hero-wheel-hint aria-hidden">
                휠 ↓ 다음 섹션, ↑ 이전
              </p>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  )
}
