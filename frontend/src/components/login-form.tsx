'use client';

import { useState, type FormEvent } from 'react';
import { createClient } from '@/lib/supabase/client';

export function LoginForm({ confirmationFailed }: { confirmationFailed: boolean }) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(confirmationFailed ? 'The confirmation link could not finish sign-in. Try signing in; if your email is not confirmed, reopen the latest confirmation link in the browser where you registered.' : '');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true); setMessage('');
    try {
      const client = createClient();
      const credentials = { email: String(form.get('email')).trim(), password: String(form.get('password')) };
      if (mode === 'signup') {
        const { data, error } = await client.auth.signUp({ ...credentials, options: { emailRedirectTo: `${window.location.origin}/auth/callback` } });
        if (error) { setMessage(error.message); return; }
        if (!data.session) { setMessage('Check your inbox for a confirmation email. Open it in this browser, then sign in. If you already have an account, use Sign in.'); return; }
      } else {
        const { error } = await client.auth.signInWithPassword(credentials);
        if (error) { setMessage('Sign-in failed. Check your email, password, and email confirmation, then try again.'); return; }
      }
      // Full navigation discards any previous user’s in-memory chat and route cache.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- discard authenticated router state on account changes
      window.location.assign('/');
    } catch { setMessage('Unable to connect. Please check your connection and try again.'); }
    finally { setBusy(false); }
  }
  return <>
    <div className="auth-tabs"><button type="button" aria-pressed={mode === 'signin'} disabled={busy} onClick={() => { setMode('signin'); setMessage(''); }}>Sign in</button><button type="button" aria-pressed={mode === 'signup'} disabled={busy} onClick={() => { setMode('signup'); setMessage(''); }}>Create account</button></div>
    <form className="auth-form" onSubmit={submit}>
      <label htmlFor="email">Email<input id="email" name="email" type="email" autoComplete="email" required disabled={busy} maxLength={254} /></label>
      <label htmlFor="password">Password<input id="password" name="password" type="password" autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} required minLength={mode === 'signup' ? 8 : 1} maxLength={128} disabled={busy} /></label>
      {mode === 'signup' && <small>Use at least 8 characters.</small>}
      <button className="button primary" disabled={busy}>{busy ? 'Please wait…' : mode === 'signin' ? 'Sign in' : 'Create account'}</button>
      {message && <p className="auth-message" role="status">{message}</p>}
    </form>
  </>;
}
