import { GridironPredictor, LEAGUE_CONFIGS } from '../components/GridironPredictor'

export function CFL() {
  return <GridironPredictor config={LEAGUE_CONFIGS.cfl} />
}
