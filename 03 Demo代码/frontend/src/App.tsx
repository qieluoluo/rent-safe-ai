import { Navigate, Route, Routes } from 'react-router-dom'

import { CaseDetailPage } from './pages/CaseDetailPage'
import { HomePage } from './pages/HomePage'
import { NewCasePage } from './pages/NewCasePage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/case/new" element={<NewCasePage />} />
      <Route path="/case/:caseId" element={<CaseDetailPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
