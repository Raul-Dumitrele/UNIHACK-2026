import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { BookingsPage } from './pages/BookingsPage'
import { IdeaDetailPage } from './pages/IdeaDetailPage'
import { IdeasPage } from './pages/IdeasPage'
import { ImpactPage } from './pages/ImpactPage'
import { NewIdeaPage } from './pages/NewIdeaPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { MapPage } from './pages/MapPage'
import { ProiectDetaliuPage } from './pages/proiect/ProiectDetaliuPage'
import { ProiectNouPage } from './pages/proiect/ProiectNouPage'
import { ProiectePage } from './pages/proiect/ProiectePage'
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
            <Route path="proiecte" element={<ProiectePage />} />
            <Route path="proiecte/nou" element={<ProiectNouPage />} />
            <Route path="proiecte/:id" element={<ProiectDetaliuPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </UserProvider>
  )
}
