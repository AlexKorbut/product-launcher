import type { Metadata } from 'next';
import Link from 'next/link';
import { getAllPosts } from '@/lib/blog';

export const metadata: Metadata = {
  title: 'Блог об автоматизации Telegram-каналов',
  description: 'Гайды и кейсы: как вести Telegram-канал на автопилоте, контент-план, рерайт постов с помощью ИИ, рост аудитории.',
  alternates: { canonical: '/blog' },
};

export default function Blog() {
  const posts = getAllPosts();
  return (
    <main className="section">
      <div className="container" style={{ maxWidth: 820 }}>
        <h2 style={{ textAlign: 'left' }}>Блог</h2>
        <p style={{ color: 'var(--muted)', marginBottom: 30 }}>
          Практика автоматизации Telegram-каналов, контент-маркетинга и работы с ИИ.
        </p>
        {posts.map((p) => (
          <Link href={`/blog/${p.slug}`} className="card-link" key={p.slug}>
            <h3>{p.title}</h3>
            <p>{p.description}</p>
            <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 8 }}>{p.date}</div>
          </Link>
        ))}
        {posts.length === 0 && <p style={{ color: 'var(--muted)' }}>Скоро здесь появятся статьи.</p>}
      </div>
    </main>
  );
}
