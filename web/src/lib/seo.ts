/**
 * SEO helper — generates Helmet props for each page.
 * All per-page SEO meta is defined here so the index.html fallback stays generic.
 */

const BASE_URL = 'https://d2d7b6u77b6we4.cloudfront.net'
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
  const canonical = props.canonical || BASE_URL
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
