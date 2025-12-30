import React from 'react';
import { signInWithPopup, signOut } from 'firebase/auth';
import { auth, googleProvider } from '../services/firebase';
import { Link, useNavigate } from 'react-router-dom';
import { ApiError, fetchUserProfile } from '../services/api';

type LoginProps = {
  initialError?: string;
};

const Login = ({ initialError }: LoginProps) => {
  const [error, setError] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);
  const navigate = useNavigate();

  React.useEffect(() => {
    if (initialError) setError(initialError);
  }, [initialError]);

  const handleGoogleLogin = async () => {
    try {
      setError('');
      setSubmitting(true);
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;

      // IMPORTANT: Login must NOT auto-register users.
      // Verify that the user exists in our DB; otherwise block login.
      await fetchUserProfile(user.uid);

      navigate('/');
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 403 && err.code === 'USER_NOT_FOUND') {
        await signOut(auth);
        setError('User not found, please, register first');
        setSubmitting(false);
        return;
      }
      await signOut(auth);
      setError(err?.message || 'Login failed');
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4 bg-black">
      <div className="w-full max-w-md p-10 glass-card">
        <h2 className="mb-2 text-4xl font-black text-center tracking-tighter">Login</h2>
        <p className="mb-8 text-center text-zinc-500 text-sm">Continue with Google to sign in</p>
        
        {error && (
          <div className="mb-6 p-3 text-xs text-red-400 bg-red-950/20 border border-red-900/50 rounded-lg text-center">
            {error}
          </div>
        )}

        <button 
          onClick={handleGoogleLogin}
          disabled={submitting}
          className="flex items-center justify-center w-full py-3 bg-zinc-900 border border-white/10 rounded-lg hover:border-white/30 transition-all font-medium group disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {submitting ? (
            <>
              <div className="w-4 h-4 mr-3 rounded-full border-2 border-white/20 border-t-white/90 animate-spin" />
              Signing in…
            </>
          ) : (
            <>
              <div className="w-4 h-4 mr-3 bg-white text-black flex items-center justify-center rounded-sm text-[10px] font-black group-hover:scale-110 transition-transform">G</div>
              Google Login
            </>
          )}
        </button>

        <p className="mt-10 text-sm text-center text-zinc-500">
          Don't have an account? <Link to="/register" className="text-white hover:underline underline-offset-4">Register here</Link>
        </p>
      </div>
    </div>
  );
};

export default Login;

