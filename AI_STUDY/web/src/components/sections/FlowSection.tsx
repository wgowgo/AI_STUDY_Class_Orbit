import { motion } from 'framer-motion'
import { FLOW_STEPS } from '../../content/site'
import {
  flowContainer,
  flowItem,
  revealItem,
  revealStagger,
} from '../../motion/variants'

export function FlowSection() {
  return (
    <motion.section
      id=flow
      className=section flow-section section--lift
      variants={revealStagger}
      initial=hidden
      whileInView=show
      viewport={{ once: true, margin: '-10% 0px' }}
    >
      <motion.div className=section-header-row variants={revealItem}>
        <p className=section-eyebrow>Flow</p>
        <h2 className=section-title>데이터 루프</h2>
      </motion.div>
      <motion.ol className=flow-pipeline variants={flowContainer}>
        {FLOW_STEPS.map((label) => (
          <motion.li key={label} variants={flowItem}>
            {label}
          </motion.li>
        ))}
      </motion.ol>
    </motion.section>
  )
}
