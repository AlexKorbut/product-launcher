'use client';

import { useEffect, useMemo, useState } from 'react';
import { api, Channel, Post } from '@/lib/api';

function startOfWeek(d: Date): Date {
  const copy = new Date(d);
  const day = (copy.getDay() + 6) % 7; // Monday = 0
  copy.setDate(copy.getDate() - day);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

const DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const STATUS_COLOR: Record<string, string> = {
  scheduled: 'blue', published: 'green', review: 'yellow', failed: 'red',
};

export default function CalendarPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));

  useEffect(() => {
    api<Post[]>('/api/posts?limit=500').then(setPosts).catch(() => {});
    api<Channel[]>('/api/channels').then(setChannels).catch(() => {});
  }, []);

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => {
      const d = new Date(weekStart);
      d.setDate(d.getDate() + i);
      return d;
    }),
    [weekStart],
  );

  const channelName = (id: number) => channels.find((c) => c.id === id)?.name || `#${id}`;

  function postsForDay(day: Date): Post[] {
    return posts
      .filter((p) => {
        const when = p.scheduled_at || p.published_at;
        if (!when) return false;
        const d = new Date(when);
        return d.toDateString() === day.toDateString();
      })
      .sort((a, b) => new Date(a.scheduled_at || a.published_at!).getTime() - new Date(b.scheduled_at || b.published_at!).getTime());
  }

  function shiftWeek(delta: number) {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + delta * 7);
    setWeekStart(d);
  }

  return (
    <div>
      <div className="row">
        <h1>Календарь контента</h1>
        <div className="spacer" />
        <button className="secondary" onClick={() => shiftWeek(-1)}>← неделя</button>{' '}
        <button className="secondary" onClick={() => setWeekStart(startOfWeek(new Date()))}>сегодня</button>{' '}
        <button className="secondary" onClick={() => shiftWeek(1)}>неделя →</button>
      </div>

      <div className="calendar-grid">
        {days.map((day, i) => (
          <div className="cal-day" key={i}>
            <div className="cal-head">{DAYS[i]} {day.getDate()}.{day.getMonth() + 1}</div>
            {postsForDay(day).map((p) => (
              <div className={`cal-post ${STATUS_COLOR[p.status] || 'gray'}`} key={p.id}
                   title={p.text.slice(0, 200)}>
                <div className="cal-time">
                  {new Date(p.scheduled_at || p.published_at!).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
                <div className="cal-channel">{channelName(p.channel_id)}</div>
                <div className="cal-text">{p.text.slice(0, 60)}</div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
