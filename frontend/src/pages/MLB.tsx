import { GridironPredictor, LEAGUE_CONFIGS } from '../components/GridironPredictor'

export function MLB() {
  return <GridironPredictor config={LEAGUE_CONFIGS.mlb} />
}
