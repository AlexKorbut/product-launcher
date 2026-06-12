'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getToken, setToken } from '@/lib/api';

function Accept() {
  const params = useSearchParams();
  const router = useRouter();
  const [state, setState] = useState<'idle' | 'ok' | 'fail' | 'auth'>('idle');
  const [error, setError] = useState('');
  const token = params.get('token') || '';

  useEffect(() => {
    if (!getToken()) {
      // remember invite and send to signup/login
      if (token) sessionStorage.setItem('pending_invite', token);
      setState('auth');
    }
  }, [token]);

  async function accept() {
    setError('');
    try {
      const res = await fetch('/api/auth/accept-invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ token }),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        throw new Error(b.detail || 'Не удалось принять приглашение');
      }
      const data = await res.json();
      setToken(data.access_token); // switch into the joined org
      setState('ok');
      setTimeout(() => router.push('/'), 1200);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка');
      setState('fail');
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card" style={{ textAlign: 'center' }}>
        <div className="auth-logo">TG Channel Studio</div>
        <h2 style={{ marginTop: 8 }}>Приглашение в команду</h2>
        {state === 'auth' && (
          <>
            <p className="muted">Войди или зарегистрируйся на тот же email, чтобы принять приглашение.</p>
            <div className="row" style={{ justifyContent: 'center', marginTop: 12 }}>
              <a className="btn" href="/login">Войти</a>
              <a className="btn secondary" href="/signup">Регистрация</a>
            </div>
          </>
        )}
        {state === 'idle' && getToken() && (
          <>
            <p className="muted">Принять приглашение и присоединиться к организации?</p>
            <button style={{ marginTop: 12 }} onClick={accept}>Принять</button>
          </>
        )}
        {state === 'ok' && <p style={{ color: 'var(--green)' }}>Готово! Перенаправляем…</p>}
        {state === 'fail' && <div className="error">{error}</div>}
      </div>
    </div>
  );
}

export default function AcceptInvitePage() {
  return <Suspense fallback={<div className="muted">…</div>}><Accept /></Suspense>;
}
