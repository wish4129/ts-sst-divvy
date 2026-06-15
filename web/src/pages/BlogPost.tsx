import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { marked } from 'marked'
import posts from '@/content/blog/posts.json'

const contentMap: Record<string, string> = {}

export default function BlogPost() {
  const { slug } = useParams<{ slug: string }>()
  const post = posts.find(p => p.slug === slug)

  const html = useMemo(() => {
    if (!slug || !contentMap[slug]) return ''
    return marked(contentMap[slug])
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
      <Helmet>
        <title>{post.title} | Divvy Blog</title>
        <link rel="canonical" href={`https://d2d7b6u77b6we4.cloudfront.net/blog/${post.slug}`} />
        <meta name="description" content={post.excerpt} />
        <meta property="og:title" content={post.title} />
        <meta property="og:description" content={post.excerpt} />
        <meta name="robots" content="index, follow" />
      </Helmet>
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
            <p className="text-gray-500 dark:text-gray-400">Content loading...</p>
          )}
        </article>
      </div>
    </div>
  )
}
