'use client';

import { useEffect, useState } from 'react';
import { applyTheme, getTheme, THEMES, ThemeId } from '@/lib/theme';

export default function SettingsPage() {
  const [active, setActive] = useState<ThemeId>('aurora');

  useEffect(() => {
    setActive(getTheme());
  }, []);

  function choose(id: ThemeId) {
    applyTheme(id);
    setActive(id);
  }

  return (
    <div>
      <h1>Настройки</h1>

      <h2>Оформление</h2>
      <p className="muted" style={{ marginTop: -4, marginBottom: 18 }}>
        Выбери тему — применяется мгновенно и запоминается на этом устройстве.
      </p>

      <div className="theme-grid">
        {THEMES.map((t) => (
          <div
            key={t.id}
            className={`theme-card ${active === t.id ? 'active' : ''}`}
            onClick={() => choose(t.id)}
          >
            {active === t.id && <div className="check">✓</div>}
            <div
              className="theme-preview"
              style={{
                background: `radial-gradient(60% 80% at 15% 0%, ${t.colors[0]}55, transparent 60%),
                             radial-gradient(50% 70% at 100% 10%, ${t.colors[1]}55, transparent 55%),
                             radial-gradient(60% 80% at 85% 110%, ${t.colors[2]}44, transparent 60%),
                             #0a0c14`,
              }}
            >
              <div className="swatch" style={{ width: 46, height: 46, left: 18, top: 38, background: t.colors[0] }} />
              <div className="swatch" style={{ width: 38, height: 38, left: 64, top: 24, background: t.colors[1] }} />
              <div className="swatch" style={{ width: 30, height: 30, left: 104, top: 52, background: t.colors[2] }} />
              <div
                style={{
                  position: 'absolute', bottom: 14, left: 18, height: 22, padding: '0 14px',
                  borderRadius: 8, display: 'flex', alignItems: 'center', color: '#fff',
                  fontSize: 11, fontWeight: 700,
                  background: `linear-gradient(120deg, ${t.colors[0]}, ${t.colors[1]} 60%, ${t.colors[2]} 130%)`,
                }}
              >
                Кнопка
              </div>
            </div>
            <div className="meta">
              <h3>{t.name}</h3>
              <p>{t.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
