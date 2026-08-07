import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { seo } from '../lib/seo'
import { marked } from 'marked'
import posts from '@/content/blog/posts.json'

// Load all blog markdown bodies at build time (Vite ?raw import — no runtime fetch).
// Slug = filename without .md, matching posts.json entries.
const rawModules = import.meta.glob('@/content/blog/*.md', { query: '?raw', import: 'default', eager: true }) as Record<string, string>

const contentMap: Record<string, string> = Object.fromEntries(
  Object.entries(rawModules).map(([path, content]) => {
    const slug = path.split('/').pop()!.replace(/\.md$/, '')
    return [slug, content]
  })
)

/** Strip the H1 title + "**Meta Description:**" header block that duplicates
 *  the page title/meta tag — only the article body should render. */
function stripHeader(md: string): string {
  return md
    .replace(/^#\s+.*\n+/, '')                       // H1 title (already rendered as <h1>)
    .replace(/^\*\*Meta Description:\*\*[^\n]*\n+/, '') // meta description (already a <meta> tag)
    .replace(/^\s*---+\s*\n/, '')                    // leading horizontal rule separator
    .trim()
}

export default function BlogPost() {
  const { slug } = useParams<{ slug: string }>()
  const post = posts.find(p => p.slug === slug)

  const html = useMemo(() => {
    if (!slug || !contentMap[slug]) return ''
    return marked(stripHeader(contentMap[slug]))
  }, [slug])

  if (!post) {
    return (
      <div className="space-y-4">
        <div className="max-w-3xl mx-auto px-4 py-16 text-center">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">Post not found</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">This blog post doesn't exist.</p>
          <Link to="/blog" className="text-emerald-600 dark:text-emerald-400 hover:underline text-sm">← Back to blog</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Helmet {...seo({
        title: post.title,
        description: post.excerpt,
        canonical: `/blog/${post.slug}`,
      })} />
      <div className="max-w-3xl mx-auto px-4 py-8">
        <Link to="/blog" className="text-sm text-emerald-600 dark:text-emerald-400 hover:underline mb-6 inline-flex items-center gap-1">
          ← Back to blog
        </Link>
        <article>
          <header className="mb-8">
            <div className="text-3xl mb-3">{post.image}</div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">{post.title}</h1>
            <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
              <span>{post.date}</span>
              <span>·</span>
              <span>{post.readTime} read</span>
            </div>
          </header>
          {html ? (
            <div
              className="prose dark:prose-invert max-w-none prose-headings:text-gray-900 dark:prose-headings:text-gray-100 prose-p:text-gray-700 dark:prose-p:text-gray-300 prose-a:text-emerald-600 dark:prose-a:text-emerald-400 prose-strong:text-gray-900 dark:prose-strong:text-gray-100"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          ) : (
            <p className="text-gray-500 dark:text-gray-400">Content unavailable.</p>
          )}
        </article>
      </div>
    </div>
  )
}
