'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, Channel } from '@/lib/api';

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // step 1
  const [channel, setChannel] = useState({ name: '', username: '', bot_token: '', topic: '', tone: 'expert' });
  const [channelId, setChannelId] = useState<number | null>(null);
  // step 2
  const [donor, setDonor] = useState('');

  async function createChannel() {
    setBusy(true); setError('');
    try {
      const ch = await api<Channel>('/api/channels', { method: 'POST', body: JSON.stringify(channel) });
      setChannelId(ch.id);
      setStep(2);
    } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка'); } finally { setBusy(false); }
  }

  async function addDonor() {
    setBusy(true); setError('');
    try {
      if (donor.trim() && channelId) {
        await api('/api/donors', { method: 'POST', body: JSON.stringify({ username: donor, channel_ids: [channelId] }) });
      }
      setStep(3);
    } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка'); } finally { setBusy(false); }
  }

  return (
    <div style={{ maxWidth: 560 }}>
      <h1>Настройка за 2 минуты</h1>
      <div className="stepper">
        {[1, 2, 3].map((s) => (
          <div key={s} className={`step ${step >= s ? 'done' : ''}`}>{s}</div>
        ))}
      </div>
      {error && <div className="error">{error}</div>}

      {step === 1 && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Шаг 1. Твой канал</h2>
          <label>Название</label>
          <input value={channel.name} onChange={(e) => setChannel({ ...channel, name: e.target.value })} />
          <label>Username (@канал)</label>
          <input value={channel.username} onChange={(e) => setChannel({ ...channel, username: e.target.value })} />
          <label>Токен бота (бот — админ канала)</label>
          <input value={channel.bot_token} onChange={(e) => setChannel({ ...channel, bot_token: e.target.value })} />
          <label>Тематика</label>
          <input value={channel.topic} onChange={(e) => setChannel({ ...channel, topic: e.target.value })} />
          <div style={{ marginTop: 16 }}>
            <button disabled={busy || !channel.name || !channel.username} onClick={createChannel}>Дальше →</button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Шаг 2. Канал-донор</h2>
          <p className="muted">Публичный канал, из которого брать посты для рерайта. Можно пропустить.</p>
          <label>@username или t.me-ссылка</label>
          <input value={donor} onChange={(e) => setDonor(e.target.value)} placeholder="@durov" />
          <div style={{ marginTop: 16 }}>
            <button disabled={busy} onClick={addDonor}>Дальше →</button>{' '}
            <button className="secondary" onClick={() => setStep(3)}>Пропустить</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Готово 🎉</h2>
          <p>Канал создан. Воркеры подхватят донора и начнут готовить посты — следи за ними в «Очереди».</p>
          <p className="muted">У тебя 500 приветственных кредитов. Можно сгенерировать первый пост прямо сейчас.</p>
          <div style={{ marginTop: 16 }}>
            <button onClick={() => router.push('/queue')}>Перейти в очередь →</button>{' '}
            <button className="secondary" onClick={() => router.push('/')}>На дашборд</button>
          </div>
        </div>
      )}
    </div>
  );
}
