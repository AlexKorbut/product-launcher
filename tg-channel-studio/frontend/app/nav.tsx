'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { clearToken } from '@/lib/api';

const items = [
  { href: '/', label: '📊 Дашборд' },
  { href: '/channels', label: '📣 Каналы' },
  { href: '/donors', label: '🔭 Доноры' },
  { href: '/queue', label: '📝 Очередь' },
];

export default function Nav() {
  const pathname = usePathname();
  if (pathname === '/login') return null;
  return (
    <aside className="sidebar">
      <div className="logo">TG Channel Studio</div>
      {items.map((it) => (
        <Link key={it.href} href={it.href} className={pathname === it.href ? 'active' : ''}>
          {it.label}
        </Link>
      ))}
      <a
        href="/login"
        onClick={() => clearToken()}
        style={{ marginTop: 24, display: 'block' }}
      >
        🚪 Выйти
      </a>
    </aside>
  );
}
