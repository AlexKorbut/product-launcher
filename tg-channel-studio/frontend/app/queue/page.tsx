'use client';

import { useEffect, useState } from 'react';
import { api, Channel, Post } from '@/lib/api';

const STATUSES = ['', 'review', 'scheduled', 'published', 'failed', 'rejected'];
const BADGE: Record<string, string> = {
  review: 'yellow', scheduled: 'blue', published: 'green', failed: 'red', rejected: 'gray', draft: 'gray',
};

export default function QueuePage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [status, setStatus] = useState('');
  const [channelId, setChannelId] = useState('');
  const [editing, setEditing] = useState<Post | null>(null);
  const [error, setError] = useState('');

  const load = () => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (channelId) params.set('channel_id', channelId);
    api<Post[]>(`/api/posts?${params}`).then(setPosts).catch((e) => setError(e.message));
  };

  useEffect(() => { api<Channel[]>('/api/channels').then(setChannels).catch(() => {}); }, []);
  useEffect(() => { load(); }, [status, channelId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function act(id: number, action: string) {
    setError('');
    try {
      await api(`/api/posts/${id}/${action}`, { method: 'POST' });
      load();
    } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка'); }
  }

  async function saveEdit() {
    if (!editing) return;
    try {
      await api(`/api/posts/${editing.id}`, { method: 'PUT', body: JSON.stringify({ text: editing.text }) });
      setEditing(null);
      load();
    } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка'); }
  }

  async function generateNew() {
    if (!channelId) { setError('Выбери канал в фильтре, чтобы сгенерировать пост с нуля'); return; }
    setError('');
    try {
      await api('/api/posts/generate', { method: 'POST', body: JSON.stringify({ channel_id: Number(channelId) }) });
      load();
    } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка'); }
  }

  const channelName = (id: number) => channels.find((c) => c.id === id)?.name || `#${id}`;

  return (
    <div>
      <div className="row">
        <h1>Очередь постов</h1>
        <div className="spacer" />
        <button onClick={generateNew}>✨ Сгенерировать с нуля</button>
      </div>

      <div className="row" style={{ marginBottom: 16 }}>
        <select style={{ width: 200 }} value={channelId} onChange={(e) => setChannelId(e.target.value)}>
          <option value="">Все каналы</option>
          {channels.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select style={{ width: 180 }} value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUSES.map((s) => <option key={s} value={s}>{s || 'Все статусы'}</option>)}
        </select>
      </div>
      {error && <div className="error">{error}</div>}

      <table>
        <thead><tr><th>Канал</th><th>Текст</th><th>Статус</th><th>Слот</th><th>似</th><th>$</th><th></th></tr></thead>
        <tbody>
          {posts.map((p) => (
            <tr key={p.id}>
              <td style={{ whiteSpace: 'nowrap' }}>{channelName(p.channel_id)}</td>
              <td><div className="post-text">{p.text.slice(0, 300)}{p.text.length > 300 ? '…' : ''}</div>
                {p.error && <div className="error">{p.error}</div>}</td>
              <td><span className={`badge ${BADGE[p.status] || 'gray'}`}>{p.status}</span></td>
              <td className="muted" style={{ whiteSpace: 'nowrap' }}>
                {p.published_at ? new Date(p.published_at).toLocaleString()
                  : p.scheduled_at ? new Date(p.scheduled_at).toLocaleString() : '—'}
              </td>
              <td className="muted">{p.similarity_to_source ? p.similarity_to_source.toFixed(2) : '—'}</td>
              <td className="muted">${p.cost_usd.toFixed(3)}</td>
              <td style={{ whiteSpace: 'nowrap' }}>
                {p.status !== 'published' && (
                  <>
                    <button className="secondary" title="Редактировать" onClick={() => setEditing(p)}>✏️</button>{' '}
                    {(p.status === 'review' || p.status === 'failed' || p.status === 'draft') && (
                      <button title="В расписание" onClick={() => act(p.id, 'approve')}>✅</button>
                    )}{' '}
                    <button className="secondary" title="Опубликовать сейчас" onClick={() => act(p.id, 'publish-now')}>🚀</button>{' '}
                    <button className="danger" title="Отклонить" onClick={() => act(p.id, 'reject')}>✖️</button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {posts.length === 0 && <tr><td colSpan={7} className="muted">Постов нет</td></tr>}
        </tbody>
      </table>

      {editing && (
        <div className="modal-backdrop" onClick={() => setEditing(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ marginTop: 0 }}>Редактирование поста</h2>
            <textarea rows={14} value={editing.text} onChange={(e) => setEditing({ ...editing, text: e.target.value })} />
            <div className="row" style={{ marginTop: 16 }}>
              <button onClick={saveEdit}>Сохранить</button>
              <button className="secondary" onClick={() => setEditing(null)}>Отмена</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
