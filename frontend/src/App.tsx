import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { onAuthStateChanged, signOut, User } from 'firebase/auth';
import { auth } from './services/firebase';
import { ApiError, fetchUserProfile } from './services/api';
import FullScreenLoader from './components/FullScreenLoader';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Charts from './pages/Charts';
import Report from './pages/Report';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [loginError, setLoginError] = useState<string>('');

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (!user) {
        setUser(null);
        setLoading(false);
        return;
      }

      // If user is authenticated with Firebase but not registered in our DB, force sign-out.
      (async () => {
        setLoading(true);
        try {
          await fetchUserProfile(user.uid);
          setLoginError('');
          setUser(user);
        } catch (e: any) {
          if (e instanceof ApiError && e.status === 403 && e.code === 'USER_NOT_FOUND') {
            setLoginError('User not found, please, register first');
          } else {
            setLoginError('Authentication failed. Please log in again.');
          }
          await signOut(auth);
          setUser(null);
        } finally {
          setLoading(false);
        }
      })();
    });
    return unsubscribe;
  }, []);

  if (loading) {
    return <FullScreenLoader label="Signing you in…" />;
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" /> : <Login initialError={loginError} />} />
        <Route path="/register" element={user ? <Navigate to="/" /> : <Register />} />
        <Route 
          path="/settings" 
          element={user ? <Settings user={user} /> : <Navigate to="/login" />} 
        />
        <Route 
          path="/charts" 
          element={user ? <Charts user={user} /> : <Navigate to="/login" />} 
        />
        <Route 
          path="/report"
          element={user ? <Report user={user} /> : <Navigate to="/login" />}
        />
        <Route 
          path="/" 
          element={user ? <Dashboard user={user} /> : <Navigate to="/login" />} 
        />
      </Routes>
    </div>
  );
}

export default App;
