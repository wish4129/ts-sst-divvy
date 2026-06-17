import { Helmet } from 'react-helmet-async'
import { seo } from '../lib/seo'
import { Link } from 'react-router-dom'
import posts from '@/content/blog/posts.json'

export default function Blog() {
  return (
    <div className="space-y-6">
      <Helmet {...seo({
        title: 'Blog — Bursa Market Analysis',
        description: 'Bursa Malaysia stock market analysis, KLSE investing guides, and portfolio strategy insights from the Divvy team.',
        canonical: 'https://d2d7b6u77b6we4.cloudfront.net/blog',
      })} />
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
          Divvy Blog
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
          Bursa market analysis, stock strategies, and KLSE insights.
        </p>
        {posts.length === 0 ? (
          <div className="text-center py-16 text-gray-500 dark:text-gray-400">
            <p className="text-lg">No posts yet.</p>
            <p className="text-sm mt-2">Check back soon for Bursa market analysis and stock guides.</p>
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 mt-8">
            {posts.map(post => (
              <Link
                key={post.slug}
                to={`/blog/${post.slug}`}
                className="group rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 transition-shadow hover:shadow-md"
              >
                <div className="text-3xl mb-3">{post.image}</div>
                <h2 className="font-semibold text-gray-900 dark:text-gray-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors mb-2">
                  {post.title}
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 line-clamp-3">
                  {post.excerpt}
                </p>
                <div className="flex items-center gap-3 text-xs text-gray-400 dark:text-gray-500">
                  <span>{post.date}</span>
                  <span>·</span>
                  <span>{post.readTime} read</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
