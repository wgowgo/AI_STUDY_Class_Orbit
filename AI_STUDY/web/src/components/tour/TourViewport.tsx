import { HeroSection } from '../hero/HeroSection'
import { TourBackdrop } from './TourBackdrop'
import { ContactTourSection } from './ContactTourSection'
import { FeaturesTourSection } from './FeaturesTourSection'
import { FlowTourSection } from './FlowTourSection'
import type { TourSectionId } from '../../content/tour'

type Props = {
  section: TourSectionId
  step: number
  backdropDimmed: boolean
  reduceMotion: boolean | null
  advance: () => void
  rewind: () => void
  onOpenAi: () => void
}

export function TourViewport({
  section,
  step,
  backdropDimmed,
  reduceMotion,
  advance,
  rewind,
  onOpenAi,
}: Props) {
  return (
    <div className=tour-viewport>
      <TourBackdrop dimmed={backdropDimmed} reduceMotion={reduceMotion} />
      <div className=tour-foreground>
        <div key={section} className=tour-section-root>
          {section === 'hero' ? (
            <HeroSection
              tourStep={step}
              reduceMotion={reduceMotion}
              advance={advance}
              rewind={rewind}
              onOpenAi={onOpenAi}
            />
          ) : null}
          {section === 'features' ? (
            <FeaturesTourSection
              step={step}
              reduceMotion={reduceMotion}
              advance={advance}
              rewind={rewind}
            />
          ) : null}
          {section === 'flow' ? (
            <FlowTourSection
              step={step}
              reduceMotion={reduceMotion}
              advance={advance}
              rewind={rewind}
            />
          ) : null}
          {section === 'contact' ? (
            <ContactTourSection
              reduceMotion={reduceMotion}
              advance={advance}
              rewind={rewind}
            />
          ) : null}
        </div>
      </div>
    </div>
  )
}
