import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import { useNavigate, useLocation } from 'react-router-dom';

export function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  
  return (
    <AppBar position="static">
      <Toolbar>
        <Typography
          variant="h6"
          component="div"
          sx={{ flexGrow: 1, cursor: 'pointer' }}
          onClick={() => navigate('/')}
        >
          Simple Image Search
        </Typography>
        
        <Button
          color="inherit"
          onClick={() => navigate('/')}
          variant={location.pathname === '/' ? 'outlined' : 'text'}
        >
          Batches
        </Button>
        
        <Button
          color="inherit"
          onClick={() => navigate('/import')}
          variant={location.pathname === '/import' ? 'outlined' : 'text'}
        >
          Import
        </Button>
      </Toolbar>
    </AppBar>
  );
}
