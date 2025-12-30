import React from 'react';
import { signInWithPopup } from 'firebase/auth';
import { auth, googleProvider } from '../services/firebase';
import { Link, useNavigate } from 'react-router-dom';
import { createUserProfile, createAccount } from '../services/api';
import { RefreshCcw } from 'lucide-react';

const Register = () => {
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const navigate = useNavigate();

  const handleGoogleRegister = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;
      
      // 1. Create user profile in users_api
      await createUserProfile(user.uid, user.displayName || 'New User');
      
      // 2. Create initial account in accounts_api as requested
      try {
        await createAccount(user.uid, {
          id: 'main-account',
          type: 'card',
          currency: { code: 'UAH', symbol: '₴' },
          balance: 0,
          title: 'Main Account',
          is_active: true
        });
      } catch (accErr: any) {
        // If account already exists (e.g. re-registering), we can ignore or log it
        console.warn('Initial account creation failed or already exists:', accErr.message);
      }

      navigate('/');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4 bg-black">
      <div className="w-full max-w-md p-10 glass-card">
        <h2 className="mb-2 text-4xl font-black text-center tracking-tighter">Register</h2>
        <p className="mb-8 text-center text-zinc-500 text-sm">
          Join CloudApi to manage your Monobank transactions. 
          Currently, we only support Google registration.
        </p>

        {error && (
          <div className="mb-6 p-3 text-xs text-red-400 bg-red-950/20 border border-red-900/50 rounded-lg text-center">
            {error}
          </div>
        )}
        
        <button 
          onClick={handleGoogleRegister}
          disabled={loading}
          className="flex items-center justify-center w-full py-4 btn-primary shadow-glow-white disabled:opacity-50 disabled:cursor-not-allowed group"
        >
          {loading ? (
            <span className="flex items-center">
              <RefreshCcw className="animate-spin mr-2" size={18} />
              Processing...
            </span>
          ) : (
            <>
              <div className="w-5 h-5 mr-3 bg-black text-white flex items-center justify-center rounded-sm text-[12px] font-black group-hover:scale-110 transition-transform">G</div>
              Sign up with Google
            </>
          )}
        </button>

        <p className="mt-10 text-sm text-center text-zinc-500">
          Already have an account? <Link to="/login" className="text-white hover:underline underline-offset-4">Login here</Link>
        </p>
      </div>
    </div>
  );
};

export default Register;
