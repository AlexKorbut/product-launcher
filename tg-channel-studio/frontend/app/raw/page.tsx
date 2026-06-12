'use client';

import { useEffect, useState } from 'react';
import { api, Channel, RawPost } from '@/lib/api';

export default function RawPage() {
  const [raw, setRaw] = useState<RawPost[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [channelId, setChannelId] = useState('');
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [done, setDone] = useState('');

  const load = () => {
    api<RawPost[]>('/api/raw?limit=80').then(setRaw).catch((e) => setError(e.message));
    api<Channel[]>('/api/channels').then(setChannels).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  async function rewrite(rawId: number) {
    if (!channelId) { setError('Выбери канал, в стиль которого переписать'); return; }
    setError(''); setDone(''); setBusyId(rawId);
    try {
      await api('/api/posts/generate', {
        method: 'POST',
        body: JSON.stringify({ channel_id: Number(channelId), raw_post_id: rawId }),
      });
      setDone('Готово — пост в очереди на модерации.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div className="row">
        <h1>Лента сырья</h1>
        <div className="spacer" />
        <select style={{ width: 240 }} value={channelId} onChange={(e) => setChannelId(e.target.value)}>
          <option value="">Канал для рерайта…</option>
          {channels.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>
      <p className="muted" style={{ marginTop: -8 }}>
        Свежие посты из подключённых каналов-доноров. Выбери канал и нажми «Переписать» — рерайт уйдёт в очередь.
      </p>
      {error && <div className="error">{error}</div>}
      {done && <div style={{ color: 'var(--green)', margin: '8px 0' }}>{done}</div>}

      <table>
        <thead><tr><th>Донор</th><th>Текст</th><th>Медиа</th><th>Получен</th><th></th></tr></thead>
        <tbody>
          {raw.map((r) => (
            <tr key={r.id}>
              <td style={{ whiteSpace: 'nowrap' }}>@{r.source_username}</td>
              <td><div className="post-text">{r.text.slice(0, 280)}{r.text.length > 280 ? '…' : ''}</div></td>
              <td>{(r.media as { type?: string }).type === 'photo' ? '🖼' : '—'}</td>
              <td className="muted" style={{ whiteSpace: 'nowrap' }}>{new Date(r.fetched_at).toLocaleString()}</td>
              <td>
                <button disabled={busyId === r.id} onClick={() => rewrite(r.id)}>
                  {busyId === r.id ? '…' : '✨ Переписать'}
                </button>
              </td>
            </tr>
          ))}
          {raw.length === 0 && (
            <tr><td colSpan={5} className="muted">Сырья пока нет — добавь доноров и дождись опроса воркером</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
