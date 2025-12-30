import React from 'react';
import { signInWithPopup, signInWithEmailAndPassword } from 'firebase/auth';
import { auth, googleProvider } from '../services/firebase';
import { Link, useNavigate } from 'react-router-dom';
import { createAccount, createUserProfile } from '../services/api';

const Login = () => {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState('');
  const navigate = useNavigate();

  const handleGoogleLogin = async () => {
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;

      // Ensure backend profile exists (prod requires this for accounts/transactions APIs)
      await createUserProfile(user.uid, user.displayName || 'New User');

      // Optional: create an initial account if missing (safe if it already exists)
      try {
        await createAccount(user.uid, {
          id: 'main-account',
          type: 'card',
          currency: { code: 'UAH', symbol: '₴' },
          balance: 0,
          title: 'Main Account',
          is_active: true
        });
      } catch (_e) {
        // Ignore if already exists
      }

      navigate('/');
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await signInWithEmailAndPassword(auth, email, password);
      navigate('/');
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4 bg-black">
      <div className="w-full max-w-md p-10 glass-card">
        <h2 className="mb-2 text-4xl font-black text-center tracking-tighter">Login</h2>
        <p className="mb-8 text-center text-zinc-500 text-sm">Enter your credentials to continue</p>
        
        {error && (
          <div className="mb-6 p-3 text-xs text-red-400 bg-red-950/20 border border-red-900/50 rounded-lg text-center">
            {error}
          </div>
        )}
        
        <form onSubmit={handleEmailLogin} className="space-y-5">
          <div>
            <label htmlFor="email" className="block mb-2 text-xs font-bold uppercase tracking-widest text-zinc-500">Email Address</label>
            <input 
              id="email"
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field"
              placeholder="name@example.com"
              required
            />
          </div>
          <div>
            <label htmlFor="password" className="block mb-2 text-xs font-bold uppercase tracking-widest text-zinc-500">Password</label>
            <input 
              id="password"
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
              placeholder="••••••••"
              required
            />
          </div>
          <button 
            type="submit"
            className="w-full py-3 mt-2 btn-primary shadow-glow-white"
          >
            Sign In
          </button>
        </form>

        <div className="relative my-10">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/5"></div>
          </div>
          <div className="relative flex justify-center text-xs uppercase tracking-widest">
            <span className="px-4 text-zinc-500 bg-black">Or continue with</span>
          </div>
        </div>

        <button 
          onClick={handleGoogleLogin}
          className="flex items-center justify-center w-full py-3 bg-zinc-900 border border-white/10 rounded-lg hover:border-white/30 transition-all font-medium group"
        >
          <div className="w-4 h-4 mr-3 bg-white text-black flex items-center justify-center rounded-sm text-[10px] font-black group-hover:scale-110 transition-transform">G</div>
          Google Login
        </button>

        <p className="mt-10 text-sm text-center text-zinc-500">
          Don't have an account? <Link to="/register" className="text-white hover:underline underline-offset-4">Register here</Link>
        </p>
      </div>
    </div>
  );
};

export default Login;

