'use client';

import { Suspense, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

function ResetForm() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get('token') || '';
  const [requesting, setRequesting] = useState(!token);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  async function requestReset(e: React.FormEvent) {
    e.preventDefault(); setError(''); setMsg('');
    const r = await fetch('/api/auth/request-reset', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (r.ok) setMsg('Если такой email есть — письмо со ссылкой отправлено.');
    else setError('Ошибка');
  }

  async function doReset(e: React.FormEvent) {
    e.preventDefault(); setError(''); setMsg('');
    const r = await fetch('/api/auth/reset', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, password }),
    });
    if (r.ok) { setMsg('Пароль обновлён. Перенаправляем на вход…'); setTimeout(() => router.push('/login'), 1200); }
    else setError('Ссылка недействительна или истекла');
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">TG Channel Studio</div>
        {requesting ? (
          <>
            <p className="muted" style={{ marginTop: 0 }}>Восстановление пароля</p>
            <form onSubmit={requestReset}>
              <label>Email</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
              <div style={{ marginTop: 18 }}><button style={{ width: '100%' }}>Отправить ссылку</button></div>
            </form>
            <p style={{ marginTop: 14 }} className="muted"><a href="/login">Назад ко входу</a></p>
          </>
        ) : (
          <>
            <p className="muted" style={{ marginTop: 0 }}>Новый пароль</p>
            <form onSubmit={doReset}>
              <label>Новый пароль (мин. 6 символов)</label>
              <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required minLength={6} />
              <div style={{ marginTop: 18 }}><button style={{ width: '100%' }}>Сменить пароль</button></div>
            </form>
            <p style={{ marginTop: 14 }} className="muted">
              <a href="#" onClick={(e) => { e.preventDefault(); setRequesting(true); }}>Запросить новую ссылку</a>
            </p>
          </>
        )}
        {msg && <div style={{ color: 'var(--green)', marginTop: 12 }}>{msg}</div>}
        {error && <div className="error">{error}</div>}
      </div>
    </div>
  );
}

export default function ResetPage() {
  return <Suspense fallback={<div className="muted">…</div>}><ResetForm /></Suspense>;
}
