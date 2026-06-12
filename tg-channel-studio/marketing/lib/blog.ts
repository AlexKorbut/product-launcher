import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';

const BLOG_DIR = path.join(process.cwd(), 'content', 'blog');

export interface PostMeta {
  slug: string;
  title: string;
  description: string;
  date: string;
  keywords: string;
}

export interface BlogPost extends PostMeta {
  content: string;
}

export function getAllSlugs(): string[] {
  if (!fs.existsSync(BLOG_DIR)) return [];
  return fs.readdirSync(BLOG_DIR).filter((f) => f.endsWith('.md')).map((f) => f.replace(/\.md$/, ''));
}

export function getPost(slug: string): BlogPost {
  const raw = fs.readFileSync(path.join(BLOG_DIR, `${slug}.md`), 'utf-8');
  const { data, content } = matter(raw);
  // YAML auto-parses dates to Date objects; normalize to YYYY-MM-DD string.
  const date =
    data.date instanceof Date ? data.date.toISOString().slice(0, 10) : String(data.date || '');
  return {
    slug,
    title: data.title || slug,
    description: data.description || '',
    date,
    keywords: data.keywords || '',
    content,
  };
}

export function getAllPosts(): PostMeta[] {
  return getAllSlugs()
    .map((slug) => {
      const { title, description, date, keywords } = getPost(slug);
      return { slug, title, description, date, keywords };
    })
    .sort((a, b) => (a.date < b.date ? 1 : -1));
}

// Minimal, safe-enough Markdown → HTML (headings, bold, lists, paragraphs, links).
export function renderMarkdown(md: string): string {
  const lines = md.split('\n');
  const html: string[] = [];
  let inList = false;
  const inline = (s: string) =>
    s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2">$1</a>');

  for (const line of lines) {
    if (/^### /.test(line)) { html.push(`<h3>${inline(line.slice(4))}</h3>`); continue; }
    if (/^## /.test(line)) { html.push(`<h2>${inline(line.slice(3))}</h2>`); continue; }
    if (/^# /.test(line)) { html.push(`<h1>${inline(line.slice(2))}</h1>`); continue; }
    if (/^[-*] /.test(line)) {
      if (!inList) { html.push('<ul>'); inList = true; }
      html.push(`<li>${inline(line.slice(2))}</li>`);
      continue;
    }
    if (inList) { html.push('</ul>'); inList = false; }
    if (line.trim() === '') continue;
    html.push(`<p>${inline(line)}</p>`);
  }
  if (inList) html.push('</ul>');
  return html.join('\n');
}
