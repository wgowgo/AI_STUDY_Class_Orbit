import { motion } from 'framer-motion'
import { STAT_ROWS } from '../../content/site'
import { easeOut } from '../../motion/variants'

const fade = { duration: 0.38, ease: easeOut }

type Props = {
  step: number
  reduceMotion: boolean | null
}

export function IntroTourSection({ step, reduceMotion }: Props) {
  const enter = reduceMotion ? false : { opacity: 0, y: 14 }
  const transition = reduceMotion ? { duration: 0 } : fade

  return (
    <section
      className=tour-section-shell tour-section--editorial
      aria-labelledby={step === 0 ? 'tour-intro-title' : undefined}
    >
      <div className=tour-single-stack>
        {step === 0 ? (
          <motion.div
            key=intro-copy
            className=tour-panel-scroll
            initial={enter}
            animate={{ opacity: 1, y: 0 }}
            transition={transition}
          >
            <p className=section-eyebrow>Intro</p>
            <h2 id=tour-intro-title className=section-headline>
              isn’t just
              <br />a dashboard.
            </h2>
            <p className=editorial-lead tour-intro-lead>
              단순한 수치 나열이 아니라, 수업이 학생에게 미칠 영향을 가늠할 수 있는
              기반 데이터를 만든 뒤, 예측, 시뮬레이션으로 이어지는 순환
              구조를 지향합니다.
            </p>
          </motion.div>
        ) : (
          <motion.div
            key=intro-stats
            className=tour-panel-scroll
            initial={enter}
            animate={{ opacity: 1, y: 0 }}
            transition={transition}
          >
            <p className=section-eyebrow>Loop</p>
            <ul className=stat-list stat-list--tour>
              {STAT_ROWS.map(([num, label]) => (
                <li key={label}>
                  <span className=stat-num>{num}</span>
                  <span className=stat-label>{label}</span>
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </div>
      <p className=tour-hint aria-hidden>
        휠 ↓ 다음 단계, ↑ 이전, 끝나면 처음으로
      </p>
    </section>
  )
}
