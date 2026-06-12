import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { NICHES, SITE } from '@/lib/site';

export function generateStaticParams() {
  return Object.keys(NICHES).map((niche) => ({ niche }));
}

export function generateMetadata({ params }: { params: { niche: string } }): Metadata {
  const n = NICHES[params.niche];
  if (!n) return {};
  const title = `Автоматизация ${n.title} в Telegram`;
  return {
    title,
    description: `${n.keyword}. ${n.intro.slice(0, 120)}`,
    alternates: { canonical: `/use-cases/${params.niche}` },
    openGraph: { title, description: n.intro },
  };
}

export default function UseCase({ params }: { params: { niche: string } }) {
  const n = NICHES[params.niche];
  if (!n) notFound();

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: `Автоматизация ${n.title} в Telegram`,
    description: n.intro,
  };

  return (
    <main className="section">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <div className="container" style={{ maxWidth: 760 }}>
        <h2 style={{ textAlign: 'left' }}>Автоматизация {n.title} в Telegram</h2>
        <p style={{ color: 'var(--muted)', fontSize: 18 }}>{n.intro}</p>

        <h3>Что делает {SITE.name}</h3>
        <ul style={{ color: 'var(--muted)' }}>
          <li>Мониторит каналы-доноры вашей ниши и забирает свежие посты</li>
          <li>Переписывает их под ваш тон через ИИ и проверяет на плагиат</li>
          <li>Публикует по расписанию — стабильный поток без ручной работы</li>
        </ul>

        <h3>Почему это работает для {n.title}</h3>
        <p style={{ color: 'var(--muted)' }}>
          Регулярность и объём — главные факторы роста в Telegram. {SITE.name} снимает с вас
          рутину поиска и переписывания контента, оставляя стратегию и тон под вашим контролем.
        </p>

        <div style={{ marginTop: 30 }}>
          <a className="btn" href={`${SITE.appUrl}/signup`}>Запустить для своего канала</a>
        </div>
      </div>
    </main>
  );
}
