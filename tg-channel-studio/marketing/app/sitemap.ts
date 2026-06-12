import type { MetadataRoute } from 'next';
import { SITE, NICHES } from '@/lib/site';
import { getAllSlugs } from '@/lib/blog';

export default function sitemap(): MetadataRoute.Sitemap {
  const base = SITE.url;
  const staticPages = ['', '/features', '/pricing', '/blog'].map((p) => ({
    url: `${base}${p}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: p === '' ? 1 : 0.8,
  }));
  const niches = Object.keys(NICHES).map((n) => ({
    url: `${base}/use-cases/${n}`,
    lastModified: new Date(),
    changeFrequency: 'monthly' as const,
    priority: 0.7,
  }));
  const posts = getAllSlugs().map((slug) => ({
    url: `${base}/blog/${slug}`,
    lastModified: new Date(),
    changeFrequency: 'monthly' as const,
    priority: 0.6,
  }));
  return [...staticPages, ...niches, ...posts];
}
