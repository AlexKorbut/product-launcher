import Link from 'next/link';
import { SITE } from '@/lib/site';

export function Header() {
  return (
    <header className="nav">
      <div className="container nav-inner">
        <Link href="/" className="brand" style={{ color: 'var(--text)' }}>{SITE.name}</Link>
        <Link href="/features">Возможности</Link>
        <Link href="/pricing">Цены</Link>
        <Link href="/blog">Блог</Link>
        <div className="nav-spacer" />
        <a className="btn ghost" href={`${SITE.appUrl}/login`}>Войти</a>
        <a className="btn" href={`${SITE.appUrl}/signup`}>Начать бесплатно</a>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="site">
      <div className="container">
        <div style={{ marginBottom: 14 }}>
          <Link href="/features">Возможности</Link>
          <Link href="/pricing">Цены</Link>
          <Link href="/blog">Блог</Link>
          <Link href="/use-cases/smm">Для агентств</Link>
        </div>
        <div>© {new Date().getFullYear()} {SITE.name}. {SITE.tagline}.</div>
      </div>
    </footer>
  );
}
