import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import {
  BookingsPage,
  IdeaDetailPage,
  IdeasPage,
  ImpactPage,
  NewIdeaPage,
  NotificationsPage,
} from './pages'
import { MapPage } from './pages/MapPage'
import { UserProvider } from './user'

export default function App() {
  return (
    <UserProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<IdeasPage />} />
            <Route path="idei/noua" element={<NewIdeaPage />} />
            <Route path="harta" element={<MapPage />} />
            <Route path="idei/:id" element={<IdeaDetailPage />} />
            <Route path="rezervari" element={<BookingsPage />} />
            <Route path="notificari" element={<NotificationsPage />} />
            <Route path="impact" element={<ImpactPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </UserProvider>
  )
}
