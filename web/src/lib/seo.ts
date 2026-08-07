/**
 * SEO helper — generates Helmet props for each page.
 * All per-page SEO meta is defined here so the index.html fallback stays generic.
 *
 * BASE_URL is env-driven (VITE_SITE_URL, set from SITE_URL at deploy time).
 * No hardcoded domain: the old CloudFront URL was deleted from AWS, and a
 * recreated distribution gets a NEW random URL (see kanban t_22f077bc9ad2).
 * Falls back to window.location.origin so canonicals always match whatever
 * domain actually serves the app.
 */

const BASE_URL = (import.meta.env.VITE_SITE_URL as string | undefined)?.replace(/\/+$/, '') || (typeof window !== 'undefined' ? window.location.origin : '')
const OG_IMAGE = `${BASE_URL}/og-image.png`
const SITE_NAME = 'Divvy — Bursa Investment Tracker'

export interface SeoProps {
  title: string
  description: string
  canonical?: string
  ogImage?: string
  noindex?: boolean
}

export function seo(props: SeoProps) {
  // Relative canonicals ('/universe') are resolved against BASE_URL so pages
  // never hardcode a domain. Absolute canonicals pass through untouched.
  const canonical = props.canonical
    ? (props.canonical.startsWith('http') ? props.canonical : `${BASE_URL}${props.canonical}`)
    : BASE_URL
  const ogImage = props.ogImage || OG_IMAGE

  return {
    title: `${props.title} | ${SITE_NAME}`,
    meta: [
      { name: 'description', content: props.description },
      { property: 'og:title', content: props.title },
      { property: 'og:description', content: props.description },
      { property: 'og:url', content: canonical },
      { property: 'og:image', content: ogImage },
      { property: 'og:image:width', content: '1200' },
      { property: 'og:image:height', content: '630' },
      { property: 'og:type', content: 'website' },
      { property: 'og:locale', content: 'en_MY' },
      { property: 'og:site_name', content: SITE_NAME },
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:url', content: canonical },
      { name: 'twitter:title', content: props.title },
      { name: 'twitter:description', content: props.description },
      { name: 'twitter:image', content: ogImage },
      ...(props.noindex
        ? [{ name: 'robots', content: 'noindex, follow' }]
        : [{ name: 'robots', content: 'index, follow' }]),
    ],
    link: [
      { rel: 'canonical', href: canonical },
    ],
  }
}
