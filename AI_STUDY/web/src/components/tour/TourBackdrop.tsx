import { motion } from 'framer-motion'
import { easeOut } from '../../motion/variants'

type Props = {
  /** false=히어로 첫 장면(밝은 스크림), true=그 외(살짝 줌, 어두운 스크림) */
  dimmed: boolean
  reduceMotion: boolean | null
}

export function TourBackdrop({ dimmed, reduceMotion }: Props) {
  const bgMotion = reduceMotion
    ? { scale: 1, y: 0 }
    : dimmed
      ? { scale: 1.09, y: -36 }
      : { scale: 1, y: 0 }

  const gridMotion = reduceMotion
    ? { rotate: 0, y: 0 }
    : dimmed
      ? { rotate: 1.5, y: -12 }
      : { rotate: 0, y: 0 }

  const scrimExtraOpacity = reduceMotion ? 0 : dimmed ? 0.4 : 0

  return (
    <div className=tour-backdrop aria-hidden>
      <motion.div
        className=hero-bg
        animate={bgMotion}
        transition={{ duration: 0.85, ease: easeOut }}
        style={{ backgroundImage: 'url(/hero-bookshelf.png)' }}
      />
      {!reduceMotion ? (
        <>
          <motion.div
            className=hero-blob hero-blob--a
            animate={{
              x: [0, 28, -8, 0],
              y: [0, -22, 12, 0],
              scale: [1, 1.12, 0.95, 1],
            }}
            transition={{
              duration: 16,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
          <motion.div
            className=hero-blob hero-blob--b
            animate={{
              x: [0, -20, 14, 0],
              y: [0, 18, -10, 0],
              scale: [1, 0.9, 1.08, 1],
            }}
            transition={{
              duration: 19,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: 1.2,
            }}
          />
          <motion.div
            className=hero-blob hero-blob--c
            animate={{
              opacity: [0.12, 0.22, 0.14, 0.12],
              scale: [1, 1.08, 1],
            }}
            transition={{
              duration: 10,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        </>
      ) : null}
      <div className=hero-scrim />
      <motion.div
        className=hero-scrim-extra
        animate={{ opacity: scrimExtraOpacity }}
        transition={{ duration: 0.55 }}
      />
      <motion.div
        className=hero-grid
        animate={gridMotion}
        transition={{ duration: 0.85, ease: easeOut }}
      />
    </div>
  )
}
