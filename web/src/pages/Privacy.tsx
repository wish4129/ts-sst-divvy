import React from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { seo } from '../lib/seo'

const Privacy: React.FC = () => {
  return (
    <>
      <Helmet {...seo({
        title: 'Privacy Policy — Divvy',
        description: 'How Divvy collects, uses, and protects your data. Covers authentication, analytics, third-party services, and your GDPR rights.',
        canonical: '/privacy',
      })} />
      <div className="max-w-3xl mx-auto py-12 px-4">
        <h1 className="text-3xl font-bold mb-8">Privacy Policy</h1>

        <div className="prose prose-lg dark:prose-invert space-y-6">
          <section>
            <h2 className="text-xl font-semibold mb-3">Data We Collect</h2>
            <p>
              Divvy collects the minimum data needed to provide our service:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Email address</strong> — collected when you sign up via Google OAuth or email/password (via Supabase Auth). Used for account identification, authentication, and service-related communications.</li>
              <li><strong>Watchlist and portfolio data</strong> — the stocks you track and your portfolio holdings are stored to provide persistent access across sessions.</li>
              <li><strong>Anonymous usage analytics</strong> — aggregated page views and feature usage to help us improve the platform. No personal identifiers are included.</li>
            </ul>
            <p>
              We do <strong>not</strong> collect personal financial information, bank account details, credit card numbers, or transaction data.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Cookies</h2>
            <p>
              Divvy uses essential cookies for authentication and session management via Supabase Auth. These are strictly necessary for the platform to function.
            </p>
            <p>
              We do <strong>not</strong> use tracking cookies, advertising cookies, third-party analytics cookies, or any persistent cross-site tracking mechanisms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Data Retention</h2>
            <p>
              Your account data is retained for as long as your account remains active. If you delete your account, all associated data is permanently removed within 30 days.
            </p>
            <p>
              Anonymous usage analytics are retained in aggregate form only and cannot be linked back to individual users after 90 days.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Third-Party Services</h2>
            <p>Divvy relies on the following third-party services:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Supabase</strong> — authentication, database, and data storage. Your email and account data are stored on Supabase's cloud infrastructure (AWS, us-east-1). <a href="https://supabase.com/privacy" target="_blank" rel="noopener noreferrer" className="text-emerald-600 dark:text-emerald-400 underline">Supabase Privacy Policy</a></li>
              <li><strong>Google OAuth</strong> — optional sign-in method. Your email and profile picture are shared with Divvy only after you explicitly authorize it. <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer" className="text-emerald-600 dark:text-emerald-400 underline">Google Privacy Policy</a></li>
            </ul>
            <p>
              We do not sell, rent, or share your personal data with any third parties not listed here.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Your Rights (GDPR)</h2>
            <p>If you are resident in the European Economic Area, you have the following rights under the General Data Protection Regulation (GDPR):</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Right to access</strong> — request a copy of the personal data we hold about you.</li>
              <li><strong>Right to rectification</strong> — request correction of inaccurate data.</li>
              <li><strong>Right to erasure</strong> — request deletion of your account and all associated data.</li>
              <li><strong>Right to data portability</strong> — request your data in a structured, machine-readable format.</li>
            </ul>
            <p>
              To exercise any of these rights, contact us at <strong>privacy@divvy.my</strong>. We will respond within 30 days.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Security</h2>
            <p>
              We implement industry-standard security measures: HTTPS for all communications, encrypted database storage, and limited access controls. However, no online service is 100% secure. You use Divvy at your own risk.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Contact</h2>
            <p>
              For privacy-related inquiries, data requests, or concerns, email us at <strong>privacy@divvy.my</strong>.
            </p>
          </section>

          <p className="text-sm text-gray-500 pt-8">
            Last updated: June 15, 2026
          </p>
        </div>

        <nav className="mt-12 pt-6 border-t border-gray-200 dark:border-gray-700 flex justify-center gap-6 text-sm">
          <Link to="/disclaimer" className="text-gray-500 hover:text-emerald-600 dark:text-gray-400 dark:hover:text-emerald-400">Disclaimer</Link>
          <Link to="/terms" className="text-gray-500 hover:text-emerald-600 dark:text-gray-400 dark:hover:text-emerald-400">Terms of Service</Link>
        </nav>
      </div>
    </>
  )
}

export default Privacy
