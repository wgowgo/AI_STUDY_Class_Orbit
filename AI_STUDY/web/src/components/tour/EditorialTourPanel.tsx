import type { ReactNode } from 'react'

type Props = {
  children: ReactNode
  advance: () => void
  rewind: () => void
  /** 기본: 히어로 인트로 패널과 동일 */
  wheelHint?: string
}

export function EditorialTourPanel({
  children,
  advance,
  rewind,
  wheelHint = '휠 ↓ 다음 섹션, ↑ 이전',
}: Props) {
  return (
    <div className=hero-ui hero-ui--panel tour-editorial-panel>
      {children}
      <div className=hero-controls hero-controls--panel>
        <button type=button className=hero-control-btn hero-control-btn--ghost onClick={rewind}>
          이전
        </button>
        <button type=button className=hero-control-btn onClick={advance}>
          다음
        </button>
        <p className=hero-wheel-hint aria-hidden>
          {wheelHint}
        </p>
      </div>
    </div>
  )
}
