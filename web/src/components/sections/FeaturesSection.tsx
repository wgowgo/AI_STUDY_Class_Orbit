import { motion, useReducedMotion } from 'framer-motion'
import { FEATURES } from '../../content/site'
import {
  featureContainer,
  featureItem,
  revealItem,
  revealStagger,
} from '../../motion/variants'

export function FeaturesSection() {
  const reduceMotion = useReducedMotion()

  return (
    <motion.section
      id="features"
      className="section features section--lift"
      variants={revealStagger}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: '-10% 0px' }}
    >
      <motion.div className="section-header-row" variants={revealItem}>
        <p className="section-eyebrow">Features</p>
        <h2 className="section-title">모듈 구성</h2>
      </motion.div>
      <motion.div className="feature-grid" variants={featureContainer}>
        {FEATURES.map((f) => (
          <motion.article
            key={f.title}
            className="feature-card"
            variants={featureItem}
            whileHover={
              reduceMotion ? undefined : { y: -4, transition: { duration: 0.2 } }
            }
          >
            <h3>{f.title}</h3>
            <p>{f.body}</p>
          </motion.article>
        ))}
      </motion.div>
    </motion.section>
  )
}
