'use client';

import { useEffect, useState } from 'react';
import { api, Channel } from '@/lib/api';

const EMPTY = {
  name: '', username: '', bot_token: '', topic: '', tone: 'expert', audience: '',
  language: 'ru', hashtags: '', banned_topics: '', prompt_template: '', signature: '',
  rewrite_level: 2, llm_provider: '', llm_model: '', auto_publish: true, posts_per_day: 4,
  quiet_hours_start: 23, quiet_hours_end: 8, tz_offset_minutes: 180,
};

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [editing, setEditing] = useState<Partial<Channel> & { bot_token?: string } | null>(null);
  const [error, setError] = useState('');
  const [checkResult, setCheckResult] = useState('');

  const load = () => api<Channel[]>('/api/channels').then(setChannels).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function save() {
    if (!editing) return;
    setError('');
    try {
      if (editing.id) {
        await api(`/api/channels/${editing.id}`, { method: 'PUT', body: JSON.stringify(editing) });
      } else {
        await api('/api/channels', { method: 'POST', body: JSON.stringify(editing) });
      }
      setEditing(null);
      load();
    } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка'); }
  }

  async function toggleStatus(ch: Channel) {
    await api(`/api/channels/${ch.id}`, {
      method: 'PUT',
      body: JSON.stringify({ ...ch, status: ch.status === 'active' ? 'paused' : 'active' }),
    });
    load();
  }

  async function remove(id: number) {
    if (!confirm('Удалить канал и все его посты?')) return;
    await api(`/api/channels/${id}`, { method: 'DELETE' });
    load();
  }

  async function check(id: number) {
    setCheckResult('Проверка…');
    try {
      const r = await api<{ bot_username: string; can_post: boolean }>(`/api/channels/${id}/check`, { method: 'POST' });
      setCheckResult(r.can_post ? `✅ @${r.bot_username} — админ, может постить` : `⚠️ @${r.bot_username} — нет прав на постинг`);
    } catch (e) { setCheckResult(`❌ ${e instanceof Error ? e.message : 'ошибка'}`); }
  }

  return (
    <div>
      <div className="row">
        <h1>Каналы</h1>
        <div className="spacer" />
        <button onClick={() => { setEditing({ ...EMPTY }); setCheckResult(''); }}>+ Добавить канал</button>
      </div>
      {error && <div className="error">{error}</div>}
      {checkResult && <div style={{ margin: '10px 0' }}>{checkResult}</div>}

      <table>
        <thead><tr><th>Название</th><th>Username</th><th>Тематика</th><th>Режим</th><th>Постов/день</th><th>Статус</th><th></th></tr></thead>
        <tbody>
          {channels.map((ch) => (
            <tr key={ch.id}>
              <td>{ch.name}</td>
              <td className="muted">@{ch.username.replace('@', '')}</td>
              <td className="muted">{ch.topic.slice(0, 60)}</td>
              <td>{ch.auto_publish ? <span className="badge blue">авто</span> : <span className="badge yellow">модерация</span>}</td>
              <td>{ch.posts_per_day}</td>
              <td><span className={`badge ${ch.status === 'active' ? 'green' : 'gray'}`}>{ch.status}</span></td>
              <td style={{ whiteSpace: 'nowrap' }}>
                <button className="secondary" onClick={() => { setEditing({ ...ch }); setCheckResult(''); }}>✏️</button>{' '}
                <button className="secondary" onClick={() => check(ch.id)}>🤖</button>{' '}
                <button className="secondary" onClick={() => toggleStatus(ch)}>{ch.status === 'active' ? '⏸' : '▶️'}</button>{' '}
                <button className="danger" onClick={() => remove(ch.id)}>🗑</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {editing && (
        <div className="modal-backdrop" onClick={() => setEditing(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ marginTop: 0 }}>{editing.id ? 'Канал' : 'Новый канал'}</h2>
            <div className="form-grid">
              <div>
                <label>Название</label>
                <input value={editing.name || ''} onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
              </div>
              <div>
                <label>Username (@канал)</label>
                <input value={editing.username || ''} onChange={(e) => setEditing({ ...editing, username: e.target.value })} />
              </div>
            </div>
            <label>Bot token {editing.id ? '(пусто = не менять)' : ''}</label>
            <input value={editing.bot_token || ''} onChange={(e) => setEditing({ ...editing, bot_token: e.target.value })} placeholder="123456:ABC…" />
            <label>Тематика</label>
            <textarea rows={2} value={editing.topic || ''} onChange={(e) => setEditing({ ...editing, topic: e.target.value })} />
            <div className="form-grid">
              <div>
                <label>Тон</label>
                <select value={editing.tone} onChange={(e) => setEditing({ ...editing, tone: e.target.value })}>
                  <option value="expert">Экспертный</option>
                  <option value="casual">Разговорный</option>
                  <option value="meme">Мемный</option>
                  <option value="formal">Формальный</option>
                </select>
              </div>
              <div>
                <label>Язык</label>
                <input value={editing.language || 'ru'} onChange={(e) => setEditing({ ...editing, language: e.target.value })} />
              </div>
            </div>
            <label>Аудитория</label>
            <input value={editing.audience || ''} onChange={(e) => setEditing({ ...editing, audience: e.target.value })} />
            <div className="form-grid">
              <div>
                <label>Хэштеги</label>
                <input value={editing.hashtags || ''} onChange={(e) => setEditing({ ...editing, hashtags: e.target.value })} />
              </div>
              <div>
                <label>Запретные темы</label>
                <input value={editing.banned_topics || ''} onChange={(e) => setEditing({ ...editing, banned_topics: e.target.value })} />
              </div>
            </div>
            <label>Подпись (добавляется к каждому посту)</label>
            <input value={editing.signature || ''} onChange={(e) => setEditing({ ...editing, signature: e.target.value })} />
            <div className="form-grid">
              <div>
                <label>LLM-провайдер</label>
                <select value={editing.llm_provider || ''} onChange={(e) => setEditing({ ...editing, llm_provider: e.target.value })}>
                  <option value="">По умолчанию (из настроек)</option>
                  <option value="anthropic">Anthropic (Claude)</option>
                  <option value="openai">OpenAI-совместимый</option>
                </select>
              </div>
              <div>
                <label>Модель (пусто = дефолт провайдера)</label>
                <input value={editing.llm_model || ''} onChange={(e) => setEditing({ ...editing, llm_model: e.target.value })} placeholder="claude-opus-4-8 / gpt-4o / …" />
              </div>
            </div>
            <div className="form-grid">
              <div>
                <label>Уровень рерайта: {editing.rewrite_level} ({['', 'лёгкий', 'глубокий', 'по мотивам'][editing.rewrite_level || 2]})</label>
                <input type="range" min={1} max={3} value={editing.rewrite_level || 2}
                  onChange={(e) => setEditing({ ...editing, rewrite_level: Number(e.target.value) })} />
              </div>
              <div>
                <label>Постов в день</label>
                <input type="number" min={1} max={48} value={editing.posts_per_day || 4}
                  onChange={(e) => setEditing({ ...editing, posts_per_day: Number(e.target.value) })} />
              </div>
            </div>
            <div className="form-grid">
              <div>
                <label>Тихие часы: с</label>
                <input type="number" min={0} max={23} value={editing.quiet_hours_start ?? 23}
                  onChange={(e) => setEditing({ ...editing, quiet_hours_start: Number(e.target.value) })} />
              </div>
              <div>
                <label>до</label>
                <input type="number" min={0} max={23} value={editing.quiet_hours_end ?? 8}
                  onChange={(e) => setEditing({ ...editing, quiet_hours_end: Number(e.target.value) })} />
              </div>
            </div>
            <label>
              <input type="checkbox" style={{ width: 'auto', marginRight: 8 }}
                checked={editing.auto_publish ?? true}
                onChange={(e) => setEditing({ ...editing, auto_publish: e.target.checked })} />
              Авто-публикация (без ручной модерации)
            </label>
            <label>Свой системный промпт (опционально, заменяет стандартный)</label>
            <textarea rows={3} value={editing.prompt_template || ''} onChange={(e) => setEditing({ ...editing, prompt_template: e.target.value })} />
            {error && <div className="error">{error}</div>}
            <div className="row" style={{ marginTop: 16 }}>
              <button onClick={save}>Сохранить</button>
              <button className="secondary" onClick={() => setEditing(null)}>Отмена</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
