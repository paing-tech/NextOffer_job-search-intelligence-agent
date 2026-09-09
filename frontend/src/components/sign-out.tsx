'use client';
import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';

export function SignOut() {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  async function signOut() {
    setBusy(true); setFailed(false);
    try {
      const { error } = await createClient().auth.signOut({ scope: 'local' });
      if (error) throw error;
      window.location.replace('/login');
    } catch { setFailed(true); setBusy(false); }
  }
  return <div><button className="button secondary" onClick={signOut} disabled={busy}>{busy ? 'Signing out…' : 'Sign out'}</button>{failed && <p role="alert">Could not sign out. Please try again.</p>}</div>;
}
