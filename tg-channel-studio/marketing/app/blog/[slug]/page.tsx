import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getAllSlugs, getPost, renderMarkdown } from '@/lib/blog';

export function generateStaticParams() {
  return getAllSlugs().map((slug) => ({ slug }));
}

export function generateMetadata({ params }: { params: { slug: string } }): Metadata {
  try {
    const post = getPost(params.slug);
    return {
      title: post.title,
      description: post.description,
      keywords: post.keywords,
      alternates: { canonical: `/blog/${post.slug}` },
      openGraph: { type: 'article', title: post.title, description: post.description },
    };
  } catch {
    return {};
  }
}

export default function BlogPost({ params }: { params: { slug: string } }) {
  let post;
  try {
    post = getPost(params.slug);
  } catch {
    notFound();
  }

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: post.title,
    description: post.description,
    datePublished: post.date,
  };

  return (
    <main className="container">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <article className="post">
        <h1>{post.title}</h1>
        <div className="post-meta">{post.date}</div>
        <div dangerouslySetInnerHTML={{ __html: renderMarkdown(post.content) }} />
      </article>
    </main>
  );
}
