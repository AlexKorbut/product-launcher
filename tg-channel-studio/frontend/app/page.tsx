'use client';

import { useEffect, useState } from 'react';
import { api, Dashboard, WorkerLog, getToken } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<Dashboard | null>(null);
  const [logs, setLogs] = useState<WorkerLog[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!getToken()) {
      router.push('/login');
      return;
    }
    const load = () => {
      api<Dashboard>('/api/dashboard').then(setData).catch((e) => setError(e.message));
      api<WorkerLog[]>('/api/dashboard/logs?limit=30').then(setLogs).catch(() => {});
    };
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [router]);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <div className="muted">Загрузка…</div>;

  return (
    <div>
      <h1>Дашборд</h1>
      <div className="cards">
        <div className="card"><div className="num">{data.raw_new}</div><div className="label">сырых постов в обработке</div></div>
        <div className="card"><div className="num">{data.total_published}</div><div className="label">опубликовано всего</div></div>
        <div className="card"><div className="num">${data.total_cost_usd.toFixed(2)}</div><div className="label">затраты на генерацию</div></div>
      </div>

      <h2>Каналы</h2>
      <table>
        <thead>
          <tr><th>Канал</th><th>Статус</th><th>В очереди</th><th>Сегодня</th><th>Ошибки</th><th>$ сегодня</th></tr>
        </thead>
        <tbody>
          {data.channels.map((c) => (
            <tr key={c.channel_id}>
              <td>{c.channel_name}</td>
              <td><span className={`badge ${c.status === 'active' ? 'green' : 'gray'}`}>{c.status}</span></td>
              <td>{c.queue}</td>
              <td>{c.published_today}</td>
              <td>{c.failed > 0 ? <span className="badge red">{c.failed}</span> : '—'}</td>
              <td>${c.cost_today_usd.toFixed(3)}</td>
            </tr>
          ))}
          {data.channels.length === 0 && (
            <tr><td colSpan={6} className="muted">Каналов пока нет — добавь первый на вкладке «Каналы»</td></tr>
          )}
        </tbody>
      </table>

      <h2>Логи воркеров</h2>
      <table>
        <thead><tr><th>Время</th><th>Воркер</th><th>Сообщение</th></tr></thead>
        <tbody>
          {logs.map((l) => (
            <tr key={l.id}>
              <td className="muted" style={{ whiteSpace: 'nowrap' }}>{new Date(l.created_at).toLocaleTimeString()}</td>
              <td><span className={`badge ${l.level === 'error' ? 'red' : l.level === 'warning' ? 'yellow' : 'blue'}`}>{l.worker}</span></td>
              <td>{l.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
