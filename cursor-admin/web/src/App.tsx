import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import UsagePage from './pages/UsagePage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import MyProjectsPage from './pages/MyProjectsPage'
import WorkspacePage from './pages/WorkspacePage'
import SpendPage from './pages/SpendPage'
import AlertsPage from './pages/AlertsPage'
import EventsPage from './pages/EventsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<UsagePage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:id" element={<ProjectDetailPage />} />
        <Route path="my-projects" element={<MyProjectsPage />} />
        <Route path="workspace" element={<WorkspacePage />} />
        <Route path="spend" element={<SpendPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="events" element={<EventsPage />} />
      </Route>
    </Routes>
  )
}
