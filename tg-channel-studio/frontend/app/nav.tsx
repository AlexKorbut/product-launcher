'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api, clearToken, getToken, Me, Alert } from '@/lib/api';

const items = [
  { href: '/', label: '📊 Дашборд' },
  { href: '/channels', label: '📣 Каналы' },
  { href: '/donors', label: '🔭 Доноры' },
  { href: '/queue', label: '📝 Очередь' },
  { href: '/calendar', label: '🗓 Календарь' },
  { href: '/billing', label: '💳 Биллинг' },
  { href: '/settings', label: '⚙️ Настройки' },
];

const PUBLIC = ['/login', '/signup'];

export default function Nav() {
  const pathname = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    if (PUBLIC.includes(pathname) || !getToken()) return;
    api<Me>('/api/auth/me').then(setMe).catch(() => {});
    api<Alert[]>('/api/dashboard/alerts').then(setAlerts).catch(() => {});
  }, [pathname]);

  if (PUBLIC.includes(pathname)) return null;

  return (
    <aside className="sidebar">
      <div className="logo">TG Channel Studio</div>
      {me && (
        <div className="credits-badge">
          <span className="num">{me.credit_balance}</span> кредитов
        </div>
      )}
      {alerts.length > 0 && (
        <Link href="/" className="alert-badge">⚠️ {alerts.length} уведомл.</Link>
      )}
      {items.map((it) => (
        <Link key={it.href} href={it.href} className={pathname === it.href ? 'active' : ''}>
          {it.label}
        </Link>
      ))}
      <a href="/login" onClick={() => clearToken()} style={{ marginTop: 24, display: 'block' }}>
        🚪 Выйти
      </a>
    </aside>
  );
}
