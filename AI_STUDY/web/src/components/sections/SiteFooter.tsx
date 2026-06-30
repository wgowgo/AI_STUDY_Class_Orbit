import { motion } from 'framer-motion'
import { revealItem, revealStagger } from '../../motion/variants'

export function SiteFooter() {
  return (
    <footer id="contact" className="footer section--lift">
      <motion.div
        className="footer-inner"
        variants={revealStagger}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: '-10% 0px' }}
      >
        <motion.p className="footer-brand" variants={revealItem}>
          Class Orbit
        </motion.p>
        <motion.p className="footer-note" variants={revealItem}>
          
        </motion.p>
        <motion.p className="footer-credit" variants={revealItem}>
          2026 — Educational AI interface shell
        </motion.p>
      </motion.div>
    </footer>
  )
}
