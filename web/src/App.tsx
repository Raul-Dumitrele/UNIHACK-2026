import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { ImpactPage } from '@/pages/ImpactPage'
import { MapPage } from '@/pages/MapPage'
import { NotificationsPage } from '@/pages/NotificationsPage'
import { ComunitatePage } from '@/pages/proiect/ComunitatePage'
import { ProiectDetaliuPage } from '@/pages/proiect/ProiectDetaliuPage'
import { ProiectNouPage } from '@/pages/proiect/ProiectNouPage'
import { ProiectePage } from '@/pages/proiect/ProiectePage'
import { TerenDetaliuPage } from '@/pages/teren/TerenDetaliuPage'
import { TerenNouPage } from '@/pages/teren/TerenNouPage'
import { UserProvider } from '@/user'

export default function App() {
  return (
    <UserProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<MapPage />} />
            <Route path="teren/nou" element={<TerenNouPage />} />
            <Route path="teren/:id" element={<TerenDetaliuPage />} />
            <Route path="proiect/nou" element={<ProiectNouPage />} />
            <Route path="comunitate" element={<ComunitatePage />} />
            <Route path="proiecte" element={<ProiectePage />} />
            <Route path="proiecte/:id" element={<ProiectDetaliuPage />} />
            <Route path="notificari" element={<NotificationsPage />} />
            <Route path="impact" element={<ImpactPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </UserProvider>
  )
}
