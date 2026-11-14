import { PendingScreen } from '../../src/components/PendingScreen'

export default function Screen() {
  return <PendingScreen title="Rezervări" endpoint="POST /bookings, PATCH /bookings/{id}" intro="Cererile tale și, pentru proprietari, cererile de aprobat sau refuzat." />
}
