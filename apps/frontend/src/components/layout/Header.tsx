import { useLocation, useNavigate } from 'react-router-dom';

export function Header() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <header className="topbar">
      <div className="topbar__inner">
        <button className="brand-button" type="button" onClick={() => navigate('/')}>
          Simple Image Search
        </button>

        <nav className="topbar__nav" aria-label="Main navigation">
          <button
            className={`nav-button ${location.pathname === '/' ? 'is-active' : ''}`}
            type="button"
            onClick={() => navigate('/')}
          >
            Batches
          </button>
          <button
            className={`nav-button ${location.pathname === '/import' ? 'is-active' : ''}`}
            type="button"
            onClick={() => navigate('/import')}
          >
            Import
          </button>
          <button
            className={`nav-button ${location.pathname === '/opencart-sql' ? 'is-active' : ''}`}
            type="button"
            onClick={() => navigate('/opencart-sql')}
          >
            OpenCart SQL
          </button>
        </nav>
      </div>
    </header>
  );
}
