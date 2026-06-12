import type { Metadata } from 'next';
import { SITE } from '@/lib/site';

export const metadata: Metadata = {
  title: 'Цены — оплата за сгенерированные посты',
  description: 'Прозрачная оплата кредитами: платите только за посты, которые ИИ реально сгенерировал. Стартовый пакет бесплатно — 500 кредитов.',
  alternates: { canonical: '/pricing' },
};

const PLANS = [
  { name: 'Старт', price: '0', unit: 'навсегда', credits: '500 кредитов при регистрации', feats: ['1 канал', 'До 3 доноров', 'ИИ-рерайт', 'Авто-публикация'], featured: false },
  { name: 'Пакет 5 000', price: '$49', unit: 'разово', credits: '5 000 кредитов', feats: ['Без лимита каналов', 'Без лимита доноров', 'Анти-плагиат', 'Календарь контента'], featured: true },
  { name: 'Пакет 20 000', price: '$149', unit: 'разово', credits: '20 000 кредитов', feats: ['Всё из пакета 5 000', 'Приоритетная генерация', 'Реферальные бонусы', 'Поддержка'], featured: false },
];

export default function Pricing() {
  return (
    <main className="section">
      <div className="container">
        <h2>Платите за результат, а не за подписку</h2>
        <p className="sub">Кредиты списываются только когда ИИ сгенерировал пост. Не пишет — не платите.</p>
        <div className="pricing">
          {PLANS.map((p) => (
            <div className={`plan ${p.featured ? 'featured' : ''}`} key={p.name}>
              <h3>{p.name}</h3>
              <div className="price">{p.price} <small>/ {p.unit}</small></div>
              <p style={{ color: 'var(--accent)' }}>{p.credits}</p>
              <ul>{p.feats.map((f) => <li key={f}>✓ {f}</li>)}</ul>
              <a className="btn" href={`${SITE.appUrl}/signup`} style={{ marginTop: 12 }}>Начать</a>
            </div>
          ))}
        </div>
        <p className="sub" style={{ marginTop: 30 }}>
          1 кредит ≈ один короткий ИИ-пост. Длинные посты с глубоким рерайтом расходуют больше — вы платите ровно за объём.
        </p>
      </div>
    </main>
  );
}
