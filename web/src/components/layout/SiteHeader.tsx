import { AnimatePresence, motion } from 'framer-motion'
import { NAV } from '../../content/site'
import type { NavId } from '../../content/site'
import { easeOut } from '../../motion/variants'

type Props = {
  menuOpen: boolean
  onMenuToggle: () => void
  onNavigate: (id: NavId) => void
  /** 투어 중 로고 클릭 시 히어로 단계로 */
  onLogoClick?: () => void
  reduceMotion: boolean | null
}

export function SiteHeader({
  menuOpen,
  onMenuToggle,
  onNavigate,
  onLogoClick,
  reduceMotion,
}: Props) {
  return (
    <>
      <motion.header
        className="site-header"
        initial={reduceMotion ? false : { opacity: 0, y: -18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: easeOut, delay: 0.08 }}
      >
        {onLogoClick ? (
          <motion.button
            type="button"
            className="logo-mark-btn"
            aria-label="히어로로 이동"
            onClick={onLogoClick}
            initial={reduceMotion ? false : { scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.45, ease: easeOut, delay: 0.12 }}
          >
            <span className="logo-mark aria-hidden" />
          </motion.button>
        ) : (
          <motion.span
            className="logo-mark"
            aria-hidden
            initial={reduceMotion ? false : { scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.45, ease: easeOut, delay: 0.12 }}
          />
        )}
        <nav className="nav-desktop" aria-label="주요 메뉴">
          {NAV.map((item, i) => (
            <motion.button
              key={item.id}
              type="button"
              className="nav-link"
              onClick={() => onNavigate(item.id)}
              initial={reduceMotion ? false : { opacity: 0, y: -8 }}
              animate={{ opacity: 0.9, y: 0 }}
              transition={{ duration: 0.4, delay: 0.18 + i * 0.05, ease: easeOut }}
              whileHover={{ opacity: 1 }}
            >
              {item.label}
            </motion.button>
          ))}
        </nav>
        <motion.button
          type="button"
          className="nav-burger"
          aria-expanded={menuOpen}
          aria-label="메뉴 열기"
          onClick={onMenuToggle}
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          whileTap={{ scale: 0.94 }}
        >
          <span />
          <span />
        </motion.button>
      </motion.header>

      <AnimatePresence>
        {menuOpen ? (
          <motion.div
            key="nav-mobile"
            className="nav-mobile"
            role="dialog"
            aria-label="모바일 메뉴"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.28 }}
          >
            {NAV.map((item, i) => (
              <motion.button
                key={item.id}
                type="button"
                className="nav-mobile-link"
                onClick={() => onNavigate(item.id)}
                initial={reduceMotion ? false : { opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 12 }}
                transition={{ delay: 0.04 + i * 0.06, ease: easeOut }}
              >
                {item.label}
              </motion.button>
            ))}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </>
  )
}
