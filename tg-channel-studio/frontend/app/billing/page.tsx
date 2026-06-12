'use client';

import { useEffect, useState } from 'react';
import { api, LedgerEntry, Me } from '@/lib/api';

const KIND_LABEL: Record<string, string> = {
  purchase: 'Покупка', debit: 'Списание', bonus: 'Бонус', refund: 'Возврат', referral: 'Реферал',
};

export default function BillingPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [packs, setPacks] = useState<Record<string, number>>({});
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [error, setError] = useState('');

  const load = () => {
    api<Me>('/api/auth/me').then(setMe).catch((e) => setError(e.message));
    api<{ packs: Record<string, number> }>('/api/billing/packs').then((d) => setPacks(d.packs)).catch(() => {});
    api<LedgerEntry[]>('/api/billing/ledger').then(setLedger).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  async function buy(priceId: string) {
    setError('');
    try {
      const r = await api<{ url: string }>('/api/billing/checkout', {
        method: 'POST', body: JSON.stringify({ price_id: priceId }),
      });
      window.location.href = r.url;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка');
    }
  }

  const referralLink = me ? `${window.location.origin}/signup?ref=${me.referral_code}` : '';

  return (
    <div>
      <h1>Биллинг</h1>
      {error && <div className="error">{error}</div>}

      <div className="cards">
        <div className="card">
          <div className="num">{me?.credit_balance ?? '—'}</div>
          <div className="label">баланс кредитов</div>
        </div>
        <div className="card">
          <div className="num">{me?.plan ?? '—'}</div>
          <div className="label">тариф</div>
        </div>
      </div>

      <h2>Пакеты кредитов</h2>
      <div className="cards">
        {Object.entries(packs).map(([priceId, credits]) => (
          <div className="card" key={priceId}>
            <div className="num">{credits.toLocaleString()}</div>
            <div className="label">кредитов</div>
            <button style={{ marginTop: 12 }} onClick={() => buy(priceId)}>Купить</button>
          </div>
        ))}
        {Object.keys(packs).length === 0 && (
          <div className="muted">Пакеты не настроены (задай STRIPE_PRICE_CREDITS в .env)</div>
        )}
      </div>

      <h2>Реферальная программа</h2>
      <p className="muted">Приглашай — вы оба получаете +300 кредитов.</p>
      <input readOnly value={referralLink} onClick={(e) => (e.target as HTMLInputElement).select()} />

      <h2>История операций</h2>
      <table>
        <thead><tr><th>Дата</th><th>Тип</th><th>Δ кредитов</th><th>Баланс</th><th>Ref</th></tr></thead>
        <tbody>
          {ledger.map((l) => (
            <tr key={l.id}>
              <td className="muted">{new Date(l.created_at).toLocaleString()}</td>
              <td>{KIND_LABEL[l.kind] || l.kind}</td>
              <td style={{ color: l.delta >= 0 ? 'var(--green)' : 'var(--red)' }}>
                {l.delta >= 0 ? '+' : ''}{l.delta}
              </td>
              <td>{l.balance_after}</td>
              <td className="muted">{l.ref}</td>
            </tr>
          ))}
          {ledger.length === 0 && <tr><td colSpan={5} className="muted">Операций пока нет</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
