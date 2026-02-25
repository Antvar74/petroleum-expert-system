/**
 * Login / Register page for PETROEXPERT.
 *
 * Premium dark UI that matches the app's industrial design system.
 * Toggles between Login and Register modes.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Box, Loader2, Eye, EyeOff, LogIn, UserPlus } from 'lucide-react';
import LanguageSelector from './LanguageSelector';
import { useAuth } from '../context/AuthContext';

const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const { login, register } = useAuth();

  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Form fields
  const [loginField, setLoginField] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');

  const resetForm = () => {
    setError('');
    setLoginField('');
    setPassword('');
    setConfirmPassword('');
    setUsername('');
    setEmail('');
    setFullName('');
    setShowPassword(false);
  };

  const handleToggleMode = () => {
    resetForm();
    setIsRegister(!isRegister);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Client-side validation (before loading state)
    if (isRegister) {
      if (password !== confirmPassword) {
        setError(t('auth.passwordMismatch'));
        return;
      }
      if (password.length < 6) {
        setError(t('auth.passwordTooShort'));
        return;
      }
    }

    setLoading(true);
    try {
      if (isRegister) {
        await register(username, email, password, fullName || undefined);
      } else {
        await login(loginField, password);
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } }; setError(axiosErr?.response?.data?.detail || t('auth.genericError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-industrial-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background decorative elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-industrial-600/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-industrial-500/5 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-industrial-600/3 rounded-full blur-[100px]" />
      </div>

      {/* Language selector top-right */}
      <div className="absolute top-6 right-6 z-10">
        <LanguageSelector />
      </div>

      {/* Main card */}
      <div className="relative w-full max-w-md">
        {/* Logo section */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-industrial-600 rounded-2xl shadow-lg shadow-industrial-900/40 mb-6">
            <Box className="text-white" size={32} />
          </div>
          <h1 className="text-3xl font-bold tracking-tighter text-white">
            PETRO<span className="text-industrial-500">EXPERT</span>
          </h1>
          <p className="text-sm text-white/30 mt-2 font-medium tracking-wide uppercase">
            {t('auth.subtitle')}
          </p>
        </div>

        {/* Form card */}
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">
          <h2 className="text-xl font-bold text-white mb-1">
            {isRegister ? t('auth.createAccount') : t('auth.welcomeBack')}
          </h2>
          <p className="text-sm text-white/40 mb-8">
            {isRegister ? t('auth.createAccountSubtitle') : t('auth.loginSubtitle')}
          </p>

          {error && (
            <div className="mb-6 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {isRegister ? (
              <>
                {/* Register fields */}
                <div>
                  <label className="block text-xs font-bold text-white/50 uppercase tracking-wider mb-2">
                    {t('auth.username')}
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="input-field h-12"
                    placeholder={t('auth.usernamePlaceholder')}
                    required
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-white/50 uppercase tracking-wider mb-2">
                    {t('auth.fullName')}
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="input-field h-12"
                    placeholder={t('auth.fullNamePlaceholder')}
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-white/50 uppercase tracking-wider mb-2">
                    {t('auth.email')}
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="input-field h-12"
                    placeholder={t('auth.emailPlaceholder')}
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-white/50 uppercase tracking-wider mb-2">
                    {t('auth.password')}
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="input-field h-12 pr-12"
                      placeholder="••••••••"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors"
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-white/50 uppercase tracking-wider mb-2">
                    {t('auth.confirmPassword')}
                  </label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="input-field h-12"
                    placeholder="••••••••"
                    required
                  />
                </div>
              </>
            ) : (
              <>
                {/* Login fields */}
                <div>
                  <label className="block text-xs font-bold text-white/50 uppercase tracking-wider mb-2">
                    {t('auth.usernameOrEmail')}
                  </label>
                  <input
                    type="text"
                    value={loginField}
                    onChange={(e) => setLoginField(e.target.value)}
                    className="input-field h-12"
                    placeholder={t('auth.loginPlaceholder')}
                    required
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-white/50 uppercase tracking-wider mb-2">
                    {t('auth.password')}
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="input-field h-12 pr-12"
                      placeholder="••••••••"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors"
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
              </>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full h-12 bg-industrial-600 hover:bg-industrial-500 disabled:bg-industrial-600/50 text-white rounded-xl transition-all font-bold text-sm tracking-tight flex items-center justify-center gap-2 shadow-lg shadow-industrial-900/30"
            >
              {loading ? (
                <Loader2 size={18} className="animate-spin" />
              ) : isRegister ? (
                <>
                  <UserPlus size={18} />
                  {t('auth.registerButton')}
                </>
              ) : (
                <>
                  <LogIn size={18} />
                  {t('auth.loginButton')}
                </>
              )}
            </button>
          </form>

          {/* Toggle mode */}
          <div className="mt-8 pt-6 border-t border-white/5 text-center">
            <p className="text-sm text-white/40">
              {isRegister ? t('auth.haveAccount') : t('auth.noAccount')}{' '}
              <button
                onClick={handleToggleMode}
                className="text-industrial-500 hover:text-industrial-400 font-bold transition-colors"
              >
                {isRegister ? t('auth.loginLink') : t('auth.registerLink')}
              </button>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-[11px] text-white/15 mt-8 font-medium">
          {t('auth.footer')}
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
