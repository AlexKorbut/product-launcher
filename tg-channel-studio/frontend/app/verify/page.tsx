'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';

function Verify() {
  const params = useSearchParams();
  const [state, setState] = useState<'loading' | 'ok' | 'fail'>('loading');

  useEffect(() => {
    const token = params.get('token');
    if (!token) { setState('fail'); return; }
    fetch('/api/auth/verify', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    }).then((r) => setState(r.ok ? 'ok' : 'fail')).catch(() => setState('fail'));
  }, [params]);

  return (
    <div className="auth-wrap">
      <div className="auth-card" style={{ textAlign: 'center' }}>
        <div className="auth-logo">TG Channel Studio</div>
        {state === 'loading' && <p className="muted">Проверяем ссылку…</p>}
        {state === 'ok' && (
          <>
            <h2 style={{ marginTop: 8 }}>Email подтверждён ✅</h2>
            <p className="muted">Спасибо! Можно возвращаться в дашборд.</p>
            <a className="btn" href="/" style={{ display: 'inline-block', marginTop: 12 }}>На дашборд</a>
          </>
        )}
        {state === 'fail' && (
          <>
            <h2 style={{ marginTop: 8 }}>Ссылка недействительна</h2>
            <p className="muted">Срок действия истёк или ссылка повреждена. Запроси новое письмо в настройках.</p>
          </>
        )}
      </div>
    </div>
  );
}

export default function VerifyPage() {
  return <Suspense fallback={<div className="muted">…</div>}><Verify /></Suspense>;
}
