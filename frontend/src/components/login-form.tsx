'use client';

import { useState, type FormEvent } from 'react';
import { useSearchParams } from 'next/navigation';
import { signIn } from 'next-auth/react';

export function LoginForm() {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const callbackUrl = useSearchParams().get('callbackUrl');
  const destination = callbackUrl && callbackUrl.startsWith('/') ? callbackUrl : '/';

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get('email')).trim();
    const password = String(form.get('password'));
    setBusy(true);
    setMessage('');
    try {
      if (mode === 'signup') {
        const res = await fetch('/api/register', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          setMessage(data.detail ?? 'Could not create the account. Try a different email.');
          return;
        }
      }

      const result = await signIn('credentials', { email, password, redirect: false });
      if (result?.error) {
        setMessage('Sign-in failed. Check your email and password, then try again.');
        return;
      }
      // Full navigation clears any previous user's in-memory chat and route cache.
      window.location.assign(destination);
    } catch {
      setMessage('Unable to connect. Please check your connection and try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="auth-tabs">
        <button type="button" aria-pressed={mode === 'signin'} disabled={busy} onClick={() => { setMode('signin'); setMessage(''); }}>Sign in</button>
        <button type="button" aria-pressed={mode === 'signup'} disabled={busy} onClick={() => { setMode('signup'); setMessage(''); }}>Create account</button>
      </div>
      <form className="auth-form" onSubmit={submit}>
        <label htmlFor="email">Email<input id="email" name="email" type="email" autoComplete="email" required disabled={busy} maxLength={254} /></label>
        <label htmlFor="password">Password<input id="password" name="password" type="password" autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} required minLength={mode === 'signup' ? 8 : 1} maxLength={128} disabled={busy} /></label>
        {mode === 'signup' && <small>Use at least 8 characters.</small>}
        <button className="button primary" disabled={busy}>{busy ? 'Please wait…' : mode === 'signin' ? 'Sign in' : 'Create account'}</button>
        {message && <p className="auth-message" role="status">{message}</p>}
      </form>
    </>
  );
}
