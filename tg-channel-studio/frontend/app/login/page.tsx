'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { setToken } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error('Неверный логин или пароль');
      const data = await res.json();
      setToken(data.access_token);
      router.push('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка входа');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">TG Channel Studio</div>
        <p className="muted" style={{ marginTop: 0, marginBottom: 22 }}>С возвращением 👋</p>
        <form onSubmit={submit}>
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          <label>Пароль</label>
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
          {error && <div className="error">{error}</div>}
          <div style={{ marginTop: 20 }}>
            <button disabled={busy} style={{ width: '100%' }}>{busy ? '...' : 'Войти'}</button>
          </div>
        </form>
        <p style={{ marginTop: 18 }} className="muted">
          Нет аккаунта? <a href="/signup">Зарегистрироваться</a>
        </p>
      </div>
    </div>
  );
}
