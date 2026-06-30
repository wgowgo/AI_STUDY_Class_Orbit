import { motion } from 'framer-motion'
import { STAT_ROWS } from '../../content/site'
import {
  revealBlock,
  revealItem,
  revealStagger,
} from '../../motion/variants'

export function IntroSection() {
  return (
    <motion.section
      id="intro"
      className="section editorial section--lift"
      variants={revealStagger}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: '-12% 0px' }}
    >
      <motion.p className="section-eyebrow" variants={revealItem}>
        Intro
      </motion.p>
      <motion.h2 className="section-headline" variants={revealBlock}>
        isn’t just
        <br />a dashboard.
      </motion.h2>
      <motion.div className="editorial-grid" variants={revealStagger}>
        <motion.p className="editorial-lead" variants={revealItem}>
          단순한 수치 나열이 아니라, 수업이 학생에게 미칠 영향을 가늠할 수 있는
          기반 데이터를 만든 뒤, 예측, 시뮬레이션으로 이어지는 순환
          구조를 지향합니다.
        </motion.p>
        <motion.ul className="stat-list" variants={revealStagger}>
          {STAT_ROWS.map(([num, label]) => (
            <motion.li key={label} variants={revealItem}>
              <span className="stat-num">{num}</span>
              <span className="stat-label">{label}</span>
            </motion.li>
          ))}
        </motion.ul>
      </motion.div>
    </motion.section>
  )
}
