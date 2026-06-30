import { motion } from 'framer-motion'
import { FLOW_STEPS, FLOW_STEPS_EN } from '../../content/site'
import { easeOut } from '../../motion/variants'
import { EditorialTourPanel } from './EditorialTourPanel'

const fade = { duration: 0.38, ease: easeOut }

type Props = {
  step: number
  reduceMotion: boolean | null
  advance: () => void
  rewind: () => void
}

export function FlowTourSection({ step, reduceMotion, advance, rewind }: Props) {
  const enter = reduceMotion ? false : { opacity: 0, y: 14 }
  const transition = reduceMotion ? { duration: 0 } : fade

  return (
    <section
      className="tour-section-shell tour-section--editorial"
      aria-labelledby={step === 0 ? 'tour-flow-title' : undefined}
    >
      <div className="tour-single-stack">
        {step === 0 ? (
          <motion.div
            key="flow-lede"
            className="tour-panel-scroll"
            initial={enter}
            animate={{ opacity: 1, y: 0 }}
            transition={transition}
          >
            <EditorialTourPanel advance={advance} rewind={rewind}>
              <p className="hero-panel-eyebrow">Flow</p>
              <h2 id="tour-flow-title" className="hero-panel-headline">
                Ingest to
                <br />
                interface.
              </h2>
              <p className="hero-panel-lead">
                <span className="hero-panel-accent" lang="en">
                  APIs → ML → (opt.) RL → LLM, SHAP → API / UI
                </span>{' '}
                공공 데이터부터 화면까지 한 줄의 루프입니다.
              </p>
            </EditorialTourPanel>
          </motion.div>
        ) : (
          <motion.div
            key="flow-pipeline"
            className="tour-panel-scroll"
            initial={enter}
            animate={{ opacity: 1, y: 0 }}
            transition={transition}
          >
            <EditorialTourPanel advance={advance} rewind={rewind}>
              <p className="hero-panel-eyebrow">Pipeline</p>
              <ul className="stat-list stat-list--tour">
                {FLOW_STEPS.map((label, i) => (
                  <li key={label}>
                    <span className="stat-num">{String(i + 1).padStart(2, '0')}</span>
                    <span className="stat-label">
                      {label}
                      <span className="stat-label-en" lang="en">
                        {FLOW_STEPS_EN[i]}
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
