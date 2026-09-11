import { Suspense } from "react";
import { LoginForm } from '@/components/login-form';

export default function LoginPage() {
  return (
    <main className="auth-page">
      <div className="auth-card">
        <h1>Sign in to NextOffer</h1>
        <Suspense>
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
