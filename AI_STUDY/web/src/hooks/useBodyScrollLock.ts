import { useEffect } from 'react'

/** 잠금 시 html/body overflow hidden (히어로 단계 진행 중) */
export function useBodyScrollLock(locked: boolean) {
  useEffect(() => {
    if (locked) {
      document.documentElement.style.overflow = 'hidden'
      document.body.style.overflow = 'hidden'
    } else {
      document.documentElement.style.overflow = ''
      document.body.style.overflow = ''
    }
    return () => {
      document.documentElement.style.overflow = ''
      document.body.style.overflow = ''
    }
  }, [locked])
}
