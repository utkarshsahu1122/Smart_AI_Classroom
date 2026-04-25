import { Link, useLocation } from 'react-router-dom'

function Navbar() {
  const location = useLocation()

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <span className="logo-icon">🎓</span>
        Smart Classroom AI
      </Link>
      <div className="navbar-links">
        <Link
          to="/faculty"
          className={location.pathname.startsWith('/faculty') ? 'active' : ''}
        >
          Faculty
        </Link>
        <Link
          to="/student/login"
          className={location.pathname.startsWith('/student') ? 'active' : ''}
        >
          Student
        </Link>
      </div>
    </nav>
  )
}

export default Navbar
