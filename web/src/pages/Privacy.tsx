import React from 'react'

const Privacy: React.FC = () => {
  return (
    <div className="max-w-3xl mx-auto py-12 px-4">
      <h1 className="text-3xl font-bold mb-8">Privacy Policy</h1>

      <div className="prose prose-lg dark:prose-invert space-y-6">
        <section>
          <h2 className="text-xl font-semibold mb-3">Data We Collect</h2>
          <p>
            Divvy collects minimal data: authentication credentials (email) if you create an account,
            and anonymous usage analytics to improve the platform. We do not collect personal financial
            information.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">Cookies</h2>
          <p>
            Divvy uses essential cookies for authentication and session management. We do not use
            tracking cookies or third-party advertising cookies.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">Third-Party Services</h2>
          <p>
            We use Supabase for authentication and data storage. Supabase's privacy policy applies
            to data stored on their infrastructure. We do not share your data with any other third parties.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">Your Rights</h2>
          <p>
            You may request deletion of your account and all associated data at any time by contacting us.
            We will comply within 30 days.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">Contact</h2>
          <p>
            For privacy-related inquiries, email us at privacy@divvy.my.
          </p>
        </section>

        <p className="text-sm text-gray-500 pt-8">
          Last updated: June 11, 2026
        </p>
      </div>
    </div>
  )
}

export default Privacy
