import { useReducedMotion } from 'framer-motion'
import { useCallback, useState } from 'react'
import { PageChrome } from './components/layout/PageChrome'
import { SiteHeader } from './components/layout/SiteHeader'
import { TourViewport } from './components/tour/TourViewport'
import { AiWorkspacePage } from './pages/AiWorkspacePage'
import type { NavId } from './content/site'
import { useWheelTour } from './hooks/useWheelTour'
import './App.css'

type AppView = 'tour' | 'ai'

function App() {
  const [view, setView] = useState<AppView>('tour')
  const [menuOpen, setMenuOpen] = useState(false)
  const reduceMotion = useReducedMotion()
  const isTourView = view === 'tour'

  const {
    section,
    step,
    backdropDimmed,
    advance,
    rewind,
    navigateToSection,
    goToHeroTour,
  } = useWheelTour({ menuOpen, enabled: isTourView })

  const handleNavigate = useCallback(
    (id: NavId) => {
      setMenuOpen(false)
      navigateToSection(id)
    },
    [navigateToSection],
  )

  const handleOpenAi = useCallback(() => {
    setView('ai')
    setMenuOpen(false)
  }, [])

  const handleBackToMain = useCallback(() => {
    setView('tour')
    goToHeroTour()
  }, [goToHeroTour])

  if (!isTourView) {
    return <AiWorkspacePage onBack={handleBackToMain} />
  }

  return (
    <div className=page>
      <PageChrome />

      <TourViewport
        section={section}
        step={step}
        backdropDimmed={backdropDimmed}
        reduceMotion={reduceMotion}
        advance={advance}
        rewind={rewind}
        onOpenAi={handleOpenAi}
      />

      <SiteHeader
        menuOpen={menuOpen}
        onMenuToggle={() => setMenuOpen((o) => !o)}
        onNavigate={handleNavigate}
        onLogoClick={goToHeroTour}
        reduceMotion={reduceMotion}
      />
    </div>
  )
}

export default App
