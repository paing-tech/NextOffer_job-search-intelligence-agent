'use client';

import { useState } from 'react';
import { signOut } from 'next-auth/react';

export function SignOut() {
  const [busy, setBusy] = useState(false);
  return (
    <div>
      <button
        className="button secondary"
        disabled={busy}
        onClick={() => {
          setBusy(true);
          void signOut({ redirectTo: '/login' });
        }}
      >
        {busy ? 'Signing out…' : 'Sign out'}
      </button>
    </div>
  );
}
