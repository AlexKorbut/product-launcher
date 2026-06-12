'use client';

const TOKEN_KEY = 'tgcs_token';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (res.status === 401 && typeof window !== 'undefined') {
    clearToken();
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Types mirroring backend schemas ---

export interface Channel {
  id: number;
  name: string;
  username: string;
  topic: string;
  tone: string;
  audience: string;
  language: string;
  hashtags: string;
  banned_topics: string;
  prompt_template: string;
  signature: string;
  rewrite_level: number;
  auto_publish: boolean;
  posts_per_day: number;
  quiet_hours_start: number;
  quiet_hours_end: number;
  tz_offset_minutes: number;
  status: string;
  donor_ids: number[];
}

export interface Donor {
  id: number;
  username: string;
  title: string;
  poll_interval_min: number;
  filters: Record<string, unknown>;
  status: string;
  last_message_id: number;
  last_polled_at: string | null;
  channel_ids: number[];
}

export interface Post {
  id: number;
  channel_id: number;
  raw_post_id: number | null;
  text: string;
  media: Record<string, unknown>;
  status: string;
  scheduled_at: string | null;
  published_at: string | null;
  error: string;
  similarity_to_source: number;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  created_at: string;
}

export interface ChannelStats {
  channel_id: number;
  channel_name: string;
  status: string;
  queue: number;
  published_today: number;
  failed: number;
  cost_today_usd: number;
}

export interface Dashboard {
  channels: ChannelStats[];
  raw_new: number;
  total_published: number;
  total_cost_usd: number;
}

export interface WorkerLog {
  id: number;
  worker: string;
  level: string;
  message: string;
  created_at: string;
}
