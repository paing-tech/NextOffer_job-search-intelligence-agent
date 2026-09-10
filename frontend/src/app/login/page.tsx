import Link from "next/link";
import { LoginForm } from '@/components/login-form';

export default function LoginPage() {
  return (
    <main className="auth-page">
      <div className="auth-card">
        <Link className="brand" href="/">NextOffer<span className="brand-dot">.</span></Link>
        <span className="eyebrow">YOUR NEXT CHAPTER STARTS HERE</span>
        <h1>A little less job-search admin.</h1>
        <p>Sign in to your workspace. Google Sheets and email connections come next.</p>
        <LoginForm />
      </div>
    </main>
  );
}
