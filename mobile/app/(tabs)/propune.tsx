import { PendingScreen } from '../../src/components/PendingScreen'

export default function Screen() {
  return <PendingScreen title="Propune o idee" endpoint="POST /ideas" intro="Descrie ideea în câteva fraze; AI-ul o transformă într-un dosar structurat." />
}
