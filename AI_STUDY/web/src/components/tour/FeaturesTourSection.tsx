import { motion } from 'framer-motion'
import { FEATURES } from '../../content/site'
import { easeOut } from '../../motion/variants'
import { EditorialTourPanel } from './EditorialTourPanel'

const fade = { duration: 0.38, ease: easeOut }

type Props = {
  step: number
  reduceMotion: boolean | null
  advance: () => void
  rewind: () => void
}

export function FeaturesTourSection({ step, reduceMotion, advance, rewind }: Props) {
  const enter = reduceMotion ? false : { opacity: 0, y: 14 }
  const transition = reduceMotion ? { duration: 0 } : fade

  return (
    <section
      className=tour-section-shell tour-section--editorial
      aria-labelledby={step === 0 ? 'tour-features-title' : undefined}
    >
      <div className=tour-single-stack>
        {step === 0 ? (
          <motion.div
            key=features-lede
            className=tour-panel-scroll
            initial={enter}
            animate={{ opacity: 1, y: 0 }}
            transition={transition}
          >
            <EditorialTourPanel advance={advance} rewind={rewind}>
              <p className=hero-panel-eyebrow>Features</p>
              <h2 id=tour-features-title className=hero-panel-headline>
                Five modules.
                <br />
                One loop.
              </h2>
              <p className=hero-panel-lead>
                <span className=hero-panel-accent lang=en>
                  Insight, risk, schedule, twin, explain
                </span>{' '}
                수업 분석부터 격차 예측, 시간표, 트윈, 설명까지 한 파이프라인으로 묶습니다.
              </p>
            </EditorialTourPanel>
          </motion.div>
        ) : (
          <motion.div
            key=features-list
            className=tour-panel-scroll
            initial={enter}
            animate={{ opacity: 1, y: 0 }}
            transition={transition}
          >
            <EditorialTourPanel advance={advance} rewind={rewind}>
              <p className=hero-panel-eyebrow>Modules</p>
              <ul className=stat-list stat-list--tour>
                {FEATURES.map((f, i) => (
                  <li key={f.title}>
                    <span className=stat-num>{String(i + 1).padStart(2, '0')}</span>
                    <span className=stat-label>
                      {f.title}
                      <span className=stat-label-en lang=en>
                        {f.labelEn}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </EditorialTourPanel>
          </motion.div>
        )}
      </div>
    </section>
  )
}
