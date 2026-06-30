import { useCallback, useEffect, useRef, useState } from 'react'
import type { NavId } from '../content/site'
import {
  NAV_ID_TO_TOUR_INDEX,
  TOUR_SECTIONS,
  TOUR_STEP_COUNT,
  type TourSectionId,
} from '../content/tour'
import { useBodyScrollLock } from './useBodyScrollLock'

const WHEEL_COOLDOWN_MS = 650
const WHEEL_DELTA_MIN = 20

type Options = {
  menuOpen: boolean
  enabled?: boolean
}

export function useWheelTour({ menuOpen, enabled = true }: Options) {
  const [sectionIndex, setSectionIndex] = useState(0)
  const [step, setStep] = useState(0)
  const wheelCooldown = useRef(false)

  useBodyScrollLock(enabled)

  const section: TourSectionId = TOUR_SECTIONS[sectionIndex]

  const runCooldown = useCallback(() => {
    wheelCooldown.current = true
    setTimeout(() => {
      wheelCooldown.current = false
    }, WHEEL_COOLDOWN_MS)
  }, [])

  /** 히어로 첫 장면만 밝은 배경, 나머지는 메인과 동일하게 살짝 줌과 스크림 */
  const backdropDimmed = !(section === 'hero' && step === 0)

  const advance = useCallback(() => {
    if (!enabled) return
    if (menuOpen) return
    if (wheelCooldown.current) return

    const maxStep = TOUR_STEP_COUNT[section] - 1
    if (step < maxStep) {
      runCooldown()
      setStep((s) => s + 1)
      return
    }

    if (sectionIndex < TOUR_SECTIONS.length - 1) {
      runCooldown()
      setSectionIndex((i) => i + 1)
      setStep(0)
      return
    }

    // 마지막 섹션 마지막 스텝 → 첫 화면으로 루프
    runCooldown()
    setSectionIndex(0)
    setStep(0)
  }, [enabled, menuOpen, section, step, sectionIndex, runCooldown])

  const rewind = useCallback(() => {
    if (!enabled) return
    if (menuOpen) return
    if (wheelCooldown.current) return

    if (step > 0) {
      runCooldown()
      setStep((s) => s - 1)
      return
    }

    if (sectionIndex > 0) {
      runCooldown()
      const newIndex = sectionIndex - 1
      const prev = TOUR_SECTIONS[newIndex]
      setSectionIndex(newIndex)
      setStep(TOUR_STEP_COUNT[prev] - 1)
    }
  }, [enabled, menuOpen, step, sectionIndex, runCooldown])

  useEffect(() => {
    if (!enabled) return

    const onWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) < WHEEL_DELTA_MIN) return
      if (e.deltaY > 0) {
        e.preventDefault()
        advance()
      } else {
        e.preventDefault()
        rewind()
      }
    }

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'PageDown') {
        e.preventDefault()
        advance()
      }
      if (e.key === 'ArrowUp' || e.key === 'PageUp') {
        e.preventDefault()
        rewind()
      }
    }

    window.addEventListener('wheel', onWheel, { passive: false })
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('wheel', onWheel)
      window.removeEventListener('keydown', onKey)
    }
  }, [advance, rewind, enabled])

  const navigateToSection = useCallback((id: NavId) => {
    const idx = NAV_ID_TO_TOUR_INDEX[id]
    setSectionIndex(idx)
    if (id === 'intro') {
      setStep(1)
      return
    }
    setStep(0)
  }, [])

  const goToHeroTour = useCallback(() => {
    setSectionIndex(0)
    setStep(0)
  }, [])

  return {
    sectionIndex,
    section,
    step,
    backdropDimmed,
    advance,
    rewind,
    navigateToSection,
    goToHeroTour,
  }
}
