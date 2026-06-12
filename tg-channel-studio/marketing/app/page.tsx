import Link from 'next/link';
import { SITE } from '@/lib/site';

const FEATURES = [
  { ico: '🔭', t: 'Каналы-доноры', d: 'Подключайте любые публичные каналы. Система мониторит их и забирает новые посты автоматически.' },
  { ico: '🤖', t: 'ИИ-рерайт', d: 'Claude переписывает посты под ваш тон и тематику — от лёгкого рерайта до материала «по мотивам».' },
  { ico: '🛡️', t: 'Анти-плагиат', d: 'Встроенная проверка похожести отклоняет слишком близкие к оригиналу тексты.' },
  { ico: '🗓', t: 'Авто-публикация', d: 'Посты выходят по расписанию с учётом тихих часов и нужной частоты — без вашего участия.' },
  { ico: '🏢', t: 'Мульти-канал', d: 'Десятки каналов из одного дашборда. Для агентств — изоляция проектов по организациям.' },
  { ico: '💳', t: 'Оплата за факт', d: 'Кредиты списываются только за сгенерированные посты. Никаких фиксированных переплат.' },
];

export default function Home() {
  return (
    <main>
      <section className="hero">
        <div className="container">
          <h1>Telegram-каналы<br />на автопилоте</h1>
          <p className="lead">{SITE.description}</p>
          <div className="cta">
            <a className="btn" href={`${SITE.appUrl}/signup`}>Начать бесплатно — 500 кредитов</a>
            <Link className="btn ghost" href="/features">Как это работает</Link>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <h2>Контент-завод без редактора</h2>
          <p className="sub">Один раз настройте тематику и доноров — дальше канал ведёт себя сам.</p>
          <div className="grid">
            {FEATURES.map((f) => (
              <div className="feature" key={f.t}>
                <div className="ico">{f.ico}</div>
                <h3>{f.t}</h3>
                <p>{f.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <h2>Как это работает</h2>
          <p className="sub">От регистрации до первого автопоста — 2 минуты.</p>
          <div className="steps">
            <div className="step-card"><h3>Подключите канал</h3><p>Добавьте свой канал и токен бота, задайте тематику и тон.</p></div>
            <div className="step-card"><h3>Выберите доноров</h3><p>Укажите публичные каналы-источники, из которых брать материал.</p></div>
            <div className="step-card"><h3>ИИ переписывает</h3><p>Claude готовит уникальные посты под ваш стиль и проверяет на плагиат.</p></div>
            <div className="step-card"><h3>Публикация сама</h3><p>Готовые посты выходят по расписанию. Вы только следите за результатом.</p></div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container" style={{ textAlign: 'center' }}>
          <h2>Готовы запустить контент-завод?</h2>
          <p className="sub">500 приветственных кредитов при регистрации. Карта не нужна.</p>
          <a className="btn" href={`${SITE.appUrl}/signup`}>Создать аккаунт</a>
        </div>
      </section>
    </main>
  );
}
