import React, { useEffect, useState } from 'react';
import { User } from 'firebase/auth';
import { fetchUserProfile, updateUserProfile, UserProfile } from '../services/api';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Key } from 'lucide-react';

interface SettingsProps {
  user: User;
}

const Settings: React.FC<SettingsProps> = ({ user }) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [monoToken, setMonoToken] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    loadProfile();
  }, [user.uid]);

  const loadProfile = async () => {
    try {
      const data = await fetchUserProfile(user.uid);
      setProfile(data);
      setMonoToken(data.mono_token || '');
    } catch (err: any) {
      setError('Failed to load profile. Make sure you are registered.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await updateUserProfile(user.uid, { mono_token: monoToken });
      setSuccess('Mono token updated successfully!');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-screen">Loading...</div>;

  return (
    <div className="max-w-2xl mx-auto p-4 sm:p-8 pt-12">
      <button 
        onClick={() => navigate('/')}
        className="flex items-center text-zinc-400 hover:text-white mb-12 transition-colors group"
      >
        <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
        Back to Dashboard
      </button>

      <div className="glass-card p-10">
        <div className="flex items-center mb-8">
          <div className="p-3 bg-white/5 rounded-xl border border-white/10 mr-4">
            <Key className="text-white" size={24} />
          </div>
          <h2 className="text-3xl font-bold tracking-tight">Mono Token</h2>
        </div>

        <p className="text-zinc-500 mb-10 leading-relaxed">
          Enter your Monobank personal API token to sync your accounts and transactions. 
          You can get your token at <a href="https://api.monobank.ua/" target="_blank" rel="noopener noreferrer" className="text-white hover:underline underline-offset-4 font-medium">api.monobank.ua</a>.
        </p>

        {error && <div className="p-4 mb-6 text-red-400 bg-red-950/20 border border-red-900/50 rounded-xl">{error}</div>}
        {success && <div className="p-4 mb-6 text-green-400 bg-green-950/20 border border-green-900/50 rounded-xl">{success}</div>}

        <form onSubmit={handleSave} className="space-y-8">
          <div>
            <label htmlFor="monoToken" className="block text-xs font-bold uppercase tracking-widest text-zinc-500 mb-3">
              Personal API Token
            </label>
            <input 
              id="monoToken"
              type="password" 
              value={monoToken}
              onChange={(e) => setMonoToken(e.target.value)}
              placeholder="Paste your token here"
              className="input-field font-mono"
            />
          </div>

          <button 
            type="submit"
            disabled={saving}
            className="flex items-center justify-center w-full py-4 btn-primary shadow-glow-white disabled:opacity-50"
          >
            {saving ? (
              <span className="flex items-center">
                <RefreshCcw className="animate-spin mr-2" size={18} />
                Saving...
              </span>
            ) : (
              <>
                <Save size={18} className="mr-2" />
                Save Changes
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Settings;

