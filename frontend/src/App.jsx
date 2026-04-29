import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import FacultyDashboard from './pages/FacultyDashboard'
import SessionDetails from './pages/SessionDetails'
import StudentLogin from './pages/StudentLogin'
import QuizView from './pages/QuizView'
import QuizResult from './pages/QuizResult'
import StudentDoubtSolver from './pages/StudentDoubtSolver'

function App() {
  return (
    <div className="app">
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/faculty" replace />} />
          <Route path="/faculty" element={<FacultyDashboard />} />
          <Route path="/faculty/session/:sessionCode" element={<SessionDetails />} />
          <Route path="/student/login" element={<StudentLogin />} />
          <Route path="/student/quiz" element={<QuizView />} />
          <Route path="/student/result" element={<QuizResult />} />
          <Route path="/student/doubts" element={<StudentDoubtSolver />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
