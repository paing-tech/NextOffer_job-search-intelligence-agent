'use client';

import { useState, type FormEvent } from 'react';
import { useSearchParams } from 'next/navigation';
import { signIn } from 'next-auth/react';

// Google's official four-color "G" mark. https://developers.google.com/identity/branding-guidelines
function GoogleLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2045c0-.6381-.0573-1.2518-.1636-1.8409H9v3.4818h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2581h2.9087c1.7018-1.5668 2.6836-3.874 2.6836-6.6154z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.4673-.8059 5.9564-2.1805l-2.9087-2.2581c-.8059.54-1.8368.8591-3.0477.8591-2.3436 0-4.3282-1.5831-5.036-3.7104H.9573v2.3318C2.4382 15.9832 5.4818 18 9 18z" />
      <path fill="#FBBC05" d="M3.964 10.71c-.18-.54-.2827-1.1168-.2827-1.71s.1027-1.17.2827-1.71V4.9582H.9573C.3477 6.1732 0 7.5477 0 9s.3477 2.8268.9573 4.0418L3.964 10.71z" />
      <path fill="#EA4335" d="M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.346l2.5813-2.5814C13.4632.8918 11.4259 0 9 0 5.4818 0 2.4382 2.0168.9573 4.9582L3.964 7.29C4.6718 5.1627 6.5564 3.5795 9 3.5795z" />
    </svg>
  );
}

// Progressive, email-first sign-in: we ask for the email first, check whether an
// account exists, and only then show the right next field — no separate sign-up
// page or sign-in/create-account toggle to choose between up front.
type Step = 'email' | 'signin' | 'signup' | 'google-only';

export function LoginForm() {
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const callbackUrl = useSearchParams().get('callbackUrl');
  const destination = callbackUrl && callbackUrl.startsWith('/') ? callbackUrl : '/';

  function reset() {
    setStep('email');
    setPassword('');
    setConfirmPassword('');
    setMessage('');
  }

  async function submitEmail(event: FormEvent) {
    event.preventDefault();
    const value = email.trim().toLowerCase();
    if (!value) return;
    setBusy(true);
    setMessage('');
    try {
      const res = await fetch('/api/auth-exists', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ email: value }),
      });
      if (!res.ok) {
        setMessage('Unable to check that email. Try again.');
        return;
      }
      const data = (await res.json()) as { exists: boolean; has_password: boolean };
      setEmail(value);
      if (!data.exists) setStep('signup');
      else if (data.has_password) setStep('signin');
      else setStep('google-only');
    } catch {
      setMessage('Unable to connect. Please check your connection and try again.');
    } finally {
      setBusy(false);
    }
  }

  async function submitSignIn(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      const result = await signIn('credentials', { email, password, redirect: false });
      if (result?.error) {
        setMessage('Incorrect password. Try again.');
        return;
      }
      window.location.assign(destination);
    } catch {
      setMessage('Unable to connect. Please check your connection and try again.');
    } finally {
      setBusy(false);
    }
  }

  async function submitSignUp(event: FormEvent) {
    event.preventDefault();
    if (password.length < 8) {
      setMessage('Use at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setMessage('Passwords do not match.');
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setMessage(data.detail ?? 'Could not create the account.');
        return;
      }
      const result = await signIn('credentials', { email, password, redirect: false });
      if (result?.error) {
        setMessage('Account created — sign in to continue.');
        setStep('signin');
        return;
      }
      window.location.assign(destination);
    } catch {
      setMessage('Unable to connect. Please check your connection and try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {step === 'email' && (
        <form className="auth-form" onSubmit={submitEmail}>
          <label htmlFor="email">Email
            <input id="email" type="email" autoComplete="email" required disabled={busy} maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
          </label>
          <button className="button primary" disabled={busy || !email.trim()}>{busy ? 'Checking…' : 'Continue'}</button>
        </form>
      )}

      {step !== 'email' && (
        <form className="auth-form" onSubmit={step === 'signin' ? submitSignIn : step === 'signup' ? submitSignUp : undefined}>
          <p className="auth-email-chip">
            <span>{email}</span>
            <button type="button" onClick={reset}>Change</button>
          </p>

          {step === 'signin' && (
            <label htmlFor="password">Password
              <input id="password" type="password" autoComplete="current-password" required disabled={busy} value={password} onChange={(e) => setPassword(e.target.value)} autoFocus />
            </label>
          )}

          {step === 'signup' && (
            <>
              <label htmlFor="password">Password
                <input id="password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} disabled={busy} value={password} onChange={(e) => setPassword(e.target.value)} autoFocus />
              </label>
              <label htmlFor="confirm-password">Confirm password
                <input id="confirm-password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} disabled={busy} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
              </label>
              <small>Use at least 8 characters.</small>
            </>
          )}

          {step === 'google-only' && (
            <p className="auth-message" role="status">This email signs in with Google — use the button below.</p>
          )}

          {step === 'signin' && (
            <button className="button primary" disabled={busy || !password}>{busy ? 'Signing in…' : 'Sign in'}</button>
          )}
          {step === 'signup' && (
            <button className="button primary" disabled={busy || !password || !confirmPassword}>{busy ? 'Creating account…' : 'Create account'}</button>
          )}
        </form>
      )}

      {message && <p className="auth-message" role="status">{message}</p>}

      <div className="auth-divider"><span>or</span></div>
      <button
        type="button"
        className="button auth-google"
        disabled={busy}
        onClick={() => { setBusy(true); void signIn('google', { callbackUrl: destination }); }}
      >
        <GoogleLogo />
        <span>Sign in with Google</span>
      </button>
    </>
  );
}
