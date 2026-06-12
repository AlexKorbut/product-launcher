'use client';

import { useEffect, useState } from 'react';
import { api, Channel, Donor } from '@/lib/api';

interface DonorForm extends Partial<Donor> {
  min_length?: number;
  skip_ads?: boolean;
  include_keywords?: string;
  exclude_keywords?: string;
}

export default function DonorsPage() {
  const [donors, setDonors] = useState<Donor[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [editing, setEditing] = useState<DonorForm | null>(null);
  const [error, setError] = useState('');

  const load = () => {
    api<Donor[]>('/api/donors').then(setDonors).catch((e) => setError(e.message));
    api<Channel[]>('/api/channels').then(setChannels).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  function openEdit(d?: Donor) {
    if (d) {
      const f = (d.filters || {}) as Record<string, unknown>;
      setEditing({
        ...d,
        min_length: Number(f.min_length || 100),
        skip_ads: f.skip_ads !== false,
        include_keywords: ((f.include_keywords as string[]) || []).join(', '),
        exclude_keywords: ((f.exclude_keywords as string[]) || []).join(', '),
      });
    } else {
      setEditing({ username: '', title: '', poll_interval_min: 15, channel_ids: [], min_length: 100, skip_ads: true, include_keywords: '', exclude_keywords: '' });
    }
  }

  async function save() {
    if (!editing) return;
    const body = {
      username: editing.username,
      title: editing.title || '',
      poll_interval_min: editing.poll_interval_min || 15,
      channel_ids: editing.channel_ids || [],
      filters: {
        min_length: editing.min_length || 0,
        skip_ads: editing.skip_ads !== false,
        include_keywords: (editing.include_keywords || '').split(',').map((s) => s.trim()).filter(Boolean),
        exclude_keywords: (editing.exclude_keywords || '').split(',').map((s) => s.trim()).filter(Boolean),
      },
    };
    try {
      if (editing.id) {
        await api(`/api/donors/${editing.id}`, { method: 'PUT', body: JSON.stringify(body) });
      } else {
        await api('/api/donors', { method: 'POST', body: JSON.stringify(body) });
      }
      setEditing(null);
      load();
    } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка'); }
  }

  async function remove(id: number) {
    if (!confirm('Удалить донора?')) return;
    await api(`/api/donors/${id}`, { method: 'DELETE' });
    load();
  }

  function toggleChannel(id: number) {
    if (!editing) return;
    const ids = new Set(editing.channel_ids || []);
    ids.has(id) ? ids.delete(id) : ids.add(id);
    setEditing({ ...editing, channel_ids: [...ids] });
  }

  return (
    <div>
      <div className="row">
        <h1>Каналы-доноры</h1>
        <div className="spacer" />
        <button onClick={() => openEdit()}>+ Добавить донора</button>
      </div>
      {error && <div className="error">{error}</div>}

      <table>
        <thead><tr><th>Донор</th><th>Каналы-получатели</th><th>Интервал</th><th>Статус</th><th>Опрошен</th><th></th></tr></thead>
        <tbody>
          {donors.map((d) => (
            <tr key={d.id}>
              <td>@{d.username} {d.title && <span className="muted">— {d.title}</span>}</td>
              <td className="muted">
                {d.channel_ids.map((id) => channels.find((c) => c.id === id)?.name || id).join(', ') || '—'}
              </td>
              <td>{d.poll_interval_min} мин</td>
              <td><span className={`badge ${d.status === 'active' ? 'green' : d.status === 'unavailable' ? 'red' : 'gray'}`}>{d.status}</span></td>
              <td className="muted">{d.last_polled_at ? new Date(d.last_polled_at).toLocaleString() : 'ещё нет'}</td>
              <td style={{ whiteSpace: 'nowrap' }}>
                <button className="secondary" onClick={() => openEdit(d)}>✏️</button>{' '}
                <button className="danger" onClick={() => remove(d.id)}>🗑</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {editing && (
        <div className="modal-backdrop" onClick={() => setEditing(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ marginTop: 0 }}>{editing.id ? 'Донор' : 'Новый донор'}</h2>
            <label>Username или ссылка t.me</label>
            <input value={editing.username || ''} onChange={(e) => setEditing({ ...editing, username: e.target.value })} placeholder="@durov или t.me/durov" />
            <div className="form-grid">
              <div>
                <label>Интервал опроса (мин)</label>
                <input type="number" min={1} value={editing.poll_interval_min || 15}
                  onChange={(e) => setEditing({ ...editing, poll_interval_min: Number(e.target.value) })} />
              </div>
              <div>
                <label>Мин. длина поста (символов)</label>
                <input type="number" min={0} value={editing.min_length || 0}
                  onChange={(e) => setEditing({ ...editing, min_length: Number(e.target.value) })} />
              </div>
            </div>
            <div className="form-grid">
              <div>
                <label>Ключевые слова (вкл.), через запятую</label>
                <input value={editing.include_keywords || ''} onChange={(e) => setEditing({ ...editing, include_keywords: e.target.value })} />
              </div>
              <div>
                <label>Стоп-слова, через запятую</label>
                <input value={editing.exclude_keywords || ''} onChange={(e) => setEditing({ ...editing, exclude_keywords: e.target.value })} />
              </div>
            </div>
            <label>
              <input type="checkbox" style={{ width: 'auto', marginRight: 8 }}
                checked={editing.skip_ads !== false}
                onChange={(e) => setEditing({ ...editing, skip_ads: e.target.checked })} />
              Пропускать рекламные посты
            </label>
            <label>Каналы-получатели</label>
            <div>
              {channels.map((c) => (
                <label key={c.id} style={{ display: 'inline-flex', alignItems: 'center', marginRight: 16 }}>
                  <input type="checkbox" style={{ width: 'auto', marginRight: 6 }}
                    checked={(editing.channel_ids || []).includes(c.id)}
                    onChange={() => toggleChannel(c.id)} />
                  {c.name}
                </label>
              ))}
              {channels.length === 0 && <span className="muted">Сначала добавь канал</span>}
            </div>
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
