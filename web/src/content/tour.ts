import type { NavId } from './site'

/** 휠 단계가 있는 전체 랜딩 순서 (히어로 포함) */
export const TOUR_SECTIONS = [
  'hero',
  'features',
  'flow',
  'contact',
] as const

export type TourSectionId = (typeof TOUR_SECTIONS)[number]

/** 각 섹션별 스텝 개수 (0 … n-1) */
export const TOUR_STEP_COUNT: Record<TourSectionId, number> = {
  hero: 2,
  features: 2,
  flow: 2,
  contact: 1,
}

/** 상단 네비 id → 투어 섹션 인덱스 (hero는 0, 네비에 없음) */
export const NAV_ID_TO_TOUR_INDEX: Record<NavId, number> = {
  intro: 0,
  features: 1,
  flow: 2,
  contact: 3,
}
