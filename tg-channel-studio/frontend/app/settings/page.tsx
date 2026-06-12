'use client';

import { useEffect, useState } from 'react';
import { applyTheme, getTheme, THEMES, ThemeId } from '@/lib/theme';
import { api, Invitation, Me, Member, OrgMembership, setToken } from '@/lib/api';

export default function SettingsPage() {
  const [active, setActive] = useState<ThemeId>('aurora');
  const [me, setMe] = useState<Me | null>(null);
  const [orgs, setOrgs] = useState<OrgMembership[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invitation[]>([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('editor');
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');

  const isOwner = me?.role === 'owner';

  function loadMe() {
    api<Me>('/api/auth/me').then(setMe).catch(() => {});
    api<OrgMembership[]>('/api/auth/orgs').then(setOrgs).catch(() => {});
  }
  function loadTeam() {
    api<Member[]>('/api/team/members').then(setMembers).catch(() => {});
    api<Invitation[]>('/api/team/invites').then(setInvites).catch(() => setInvites([]));
  }

  useEffect(() => { setActive(getTheme()); loadMe(); loadTeam(); }, []);

  function choose(id: ThemeId) { applyTheme(id); setActive(id); }

  async function switchOrg(orgId: number) {
    const r = await api<{ access_token: string }>('/api/auth/switch-org', {
      method: 'POST', body: JSON.stringify({ org_id: orgId }),
    });
    setToken(r.access_token);
    window.location.reload();
  }

  async function resendVerify() {
    await api('/api/auth/request-verify', { method: 'POST' });
    setMsg('Письмо отправлено — проверь почту.');
  }

  async function invite(e: React.FormEvent) {
    e.preventDefault(); setError(''); setMsg('');
    try {
      await api('/api/team/invite', { method: 'POST', body: JSON.stringify({ email: inviteEmail, role: inviteRole }) });
      setInviteEmail(''); setMsg('Приглашение отправлено.'); loadTeam();
    } catch (err) { setError(err instanceof Error ? err.message : 'Ошибка'); }
  }

  async function changeRole(userId: number, role: string) {
    await api(`/api/team/members/${userId}/role`, { method: 'POST', body: JSON.stringify({ role }) });
    loadTeam();
  }
  async function removeMember(userId: number) {
    if (!confirm('Удалить участника из организации?')) return;
    await api(`/api/team/members/${userId}`, { method: 'DELETE' });
    loadTeam();
  }
  async function cancelInvite(id: number) {
    await api(`/api/team/invites/${id}`, { method: 'DELETE' });
    loadTeam();
  }

  return (
    <div>
      <h1>Настройки</h1>
      {error && <div className="error">{error}</div>}
      {msg && <div style={{ color: 'var(--green)', margin: '8px 0' }}>{msg}</div>}

      {me && !me.email_verified && (
        <div className="alerts-panel">
          <div className="row">
            <span>📧 Email <b>{me.email}</b> не подтверждён.</span>
            <div className="spacer" />
            <button className="secondary" onClick={resendVerify}>Отправить письмо</button>
          </div>
        </div>
      )}

      <h2>Оформление</h2>
      <p className="muted" style={{ marginTop: -4, marginBottom: 18 }}>
        Выбери тему — применяется мгновенно и запоминается на этом устройстве.
      </p>
      <div className="theme-grid">
        {THEMES.map((t) => (
          <div key={t.id} className={`theme-card ${active === t.id ? 'active' : ''}`} onClick={() => choose(t.id)}>
            {active === t.id && <div className="check">✓</div>}
            <div className="theme-preview" style={{
              background: `radial-gradient(60% 80% at 15% 0%, ${t.colors[0]}55, transparent 60%),
                           radial-gradient(50% 70% at 100% 10%, ${t.colors[1]}55, transparent 55%),
                           radial-gradient(60% 80% at 85% 110%, ${t.colors[2]}44, transparent 60%), #0a0c14` }}>
              <div className="swatch" style={{ width: 46, height: 46, left: 18, top: 38, background: t.colors[0] }} />
              <div className="swatch" style={{ width: 38, height: 38, left: 64, top: 24, background: t.colors[1] }} />
              <div className="swatch" style={{ width: 30, height: 30, left: 104, top: 52, background: t.colors[2] }} />
              <div style={{ position: 'absolute', bottom: 14, left: 18, height: 22, padding: '0 14px',
                borderRadius: 8, display: 'flex', alignItems: 'center', color: '#fff', fontSize: 11, fontWeight: 700,
                background: `linear-gradient(120deg, ${t.colors[0]}, ${t.colors[1]} 60%, ${t.colors[2]} 130%)` }}>Кнопка</div>
            </div>
            <div className="meta"><h3>{t.name}</h3><p>{t.description}</p></div>
          </div>
        ))}
      </div>

      {orgs.length > 1 && (
        <>
          <h2>Организации</h2>
          <table>
            <thead><tr><th>Организация</th><th>Роль</th><th></th></tr></thead>
            <tbody>
              {orgs.map((o) => (
                <tr key={o.org_id}>
                  <td>{o.org_name} {o.org_id === me?.org_id && <span className="badge blue">текущая</span>}</td>
                  <td><span className="badge gray">{o.role}</span></td>
                  <td>{o.org_id !== me?.org_id && <button className="secondary" onClick={() => switchOrg(o.org_id)}>Переключиться</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <h2>Команда</h2>
      <table>
        <thead><tr><th>Email</th><th>Роль</th>{isOwner && <th></th>}</tr></thead>
        <tbody>
          {members.map((m) => (
            <tr key={m.user_id}>
              <td>{m.email} {m.user_id === me?.user_id && <span className="muted">(вы)</span>}</td>
              <td>
                {isOwner && m.user_id !== me?.user_id ? (
                  <select style={{ width: 130 }} value={m.role} onChange={(e) => changeRole(m.user_id, e.target.value)}>
                    <option value="owner">owner</option>
                    <option value="editor">editor</option>
                  </select>
                ) : <span className="badge gray">{m.role}</span>}
              </td>
              {isOwner && (
                <td>{m.user_id !== me?.user_id && <button className="danger" onClick={() => removeMember(m.user_id)}>Удалить</button>}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {isOwner && (
        <>
          <h2>Пригласить участника</h2>
          <form onSubmit={invite} className="row" style={{ alignItems: 'flex-end', gap: 12 }}>
            <div style={{ flex: 1 }}>
              <label>Email</label>
              <input value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} type="email" required />
            </div>
            <div style={{ width: 150 }}>
              <label>Роль</label>
              <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                <option value="editor">editor</option>
                <option value="owner">owner</option>
              </select>
            </div>
            <button>Пригласить</button>
          </form>

          {invites.length > 0 && (
            <>
              <h2>Ожидают принятия</h2>
              <table>
                <thead><tr><th>Email</th><th>Роль</th><th></th></tr></thead>
                <tbody>
                  {invites.map((i) => (
                    <tr key={i.id}>
                      <td>{i.email}</td>
                      <td><span className="badge yellow">{i.role}</span></td>
                      <td><button className="secondary" onClick={() => cancelInvite(i.id)}>Отменить</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      )}
    </div>
  );
}
