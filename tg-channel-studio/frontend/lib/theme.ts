'use client';

export type ThemeId = 'aurora' | 'ember' | 'emerald';

export interface Theme {
  id: ThemeId;
  name: string;
  description: string;
  colors: [string, string, string]; // preview swatch colors
}

export const THEMES: Theme[] = [
  {
    id: 'aurora',
    name: 'Aurora',
    description: 'Глубокий navy с indigo → violet → cyan. Классика по умолчанию.',
    colors: ['#6c8cff', '#a06bff', '#36d2c9'],
  },
  {
    id: 'ember',
    name: 'Ember',
    description: 'Тёплый уголь с orange → pink → amber. Энергично и ярко.',
    colors: ['#ff8a4c', '#ff5d8f', '#ffb648'],
  },
  {
    id: 'emerald',
    name: 'Emerald',
    description: 'Изумрудно-чёрный с green → cyan → lime. Свежо и технологично.',
    colors: ['#34d399', '#22d3ee', '#a3e635'],
  },
];

const KEY = 'tgcs_theme';

export function getTheme(): ThemeId {
  if (typeof window === 'undefined') return 'aurora';
  return (localStorage.getItem(KEY) as ThemeId) || 'aurora';
}

export function applyTheme(id: ThemeId) {
  if (typeof document === 'undefined') return;
  if (id === 'aurora') {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = id;
  }
  localStorage.setItem(KEY, id);
}
