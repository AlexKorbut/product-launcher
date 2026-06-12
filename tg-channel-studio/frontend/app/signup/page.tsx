'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { setToken } from '@/lib/api';

function SignupForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [orgName, setOrgName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const res = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email, password, org_name: orgName || 'Моя организация',
          referral_code: params.get('ref') || undefined,
        }),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        throw new Error(b.detail || 'Не удалось зарегистрироваться');
      }
      const data = await res.json();
      setToken(data.access_token);
      router.push('/onboarding');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 380, margin: '70px auto' }}>
      <h1>Регистрация</h1>
      <p className="muted">500 приветственных кредитов сразу после регистрации.</p>
      <form onSubmit={submit}>
        <label>Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        <label>Пароль (мин. 6 символов)</label>
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required minLength={6} />
        <label>Название организации</label>
        <input value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="Моя организация" />
        {params.get('ref') && <p className="muted">Реферальный код: {params.get('ref')} (+300 кредитов)</p>}
        {error && <div className="error">{error}</div>}
        <div style={{ marginTop: 18 }}>
          <button disabled={busy}>{busy ? '...' : 'Создать аккаунт'}</button>
        </div>
      </form>
      <p style={{ marginTop: 16 }} className="muted">
        Уже есть аккаунт? <a href="/login">Войти</a>
      </p>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={<div className="muted">Загрузка…</div>}>
      <SignupForm />
    </Suspense>
  );
}
