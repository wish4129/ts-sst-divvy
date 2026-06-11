import React from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { seo } from '../lib/seo'

const Disclaimer: React.FC = () => {
  return (
    <>
      <Helmet {...seo({
        title: 'Disclaimer — Divvy',
        description: 'Divvy provides stock analysis for informational purposes only. No financial advice. Read our full disclaimer including Malaysian CMSA compliance.',
        canonical: 'https://d2d7b6u77b6we4.cloudfront.net/disclaimer',
      })} />
      <div className="max-w-3xl mx-auto py-12 px-4">
        <h1 className="text-3xl font-bold mb-8">Disclaimer</h1>

        <div className="prose prose-lg dark:prose-invert space-y-6">
          <section>
            <h2 className="text-xl font-semibold mb-3">No Financial Advice</h2>
            <p>
              Divvy provides stock screening, scoring, analysis reports, and AI-generated forecasts for <strong>informational and educational purposes only</strong>.
              Nothing on this platform constitutes financial advice, investment recommendations, or a solicitation to buy, sell, or hold any security.
            </p>
            <p className="font-medium text-amber-600 dark:text-amber-400">
              You assume all risk for any investment decisions you make based on information from Divvy.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Malaysian Legal Compliance</h2>
            <p>
              Divvy is operated from Malaysia and complies with applicable Malaysian securities laws.
              The information, reports, and analysis provided on this platform do <strong>not</strong> constitute
              a recommendation or invitation to invest in any capital market product under the
              <strong> Capital Markets and Services Act 2007 (CMSA)</strong>.
            </p>
            <p>
              Divvy is <strong>not</strong> licensed as a financial advisor, investment advisor, or
              securities dealer under the CMSA. Users should consult a licensed financial advisor
              registered with the Securities Commission Malaysia before making any investment decisions.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">No Liability</h2>
            <p>
              Divvy and its creators <strong>do not accept any liability</strong> for any financial loss,
              profit loss, missed opportunities, or damages arising from the use of information, reports,
              forecasts, or analysis provided on this platform.
            </p>
            <p>
              You use Divvy entirely at your own risk. All investment decisions are your sole responsibility.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Data Accuracy</h2>
            <p>
              Stock data is sourced from third-party providers (yfinance / Yahoo Finance, Bursa Malaysia
              public filings) and may contain errors, inaccuracies, delays, or omissions. Data is provided
              "as is" without any guarantee of completeness or timeliness.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">AI-Generated Reports</h2>
            <p>
              Some analysis reports, scores, and forecasts on Divvy are AI-generated using statistical models
              and machine learning. These are <strong>not</strong> human financial analysis.
              AI-generated content may contain:
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Factual errors or hallucinated data</li>
              <li>Flawed or incomplete reasoning</li>
              <li>Outdated or irrelevant information</li>
              <li>Incorrect forecasts or predictions</li>
            </ul>
            <p>
              Always conduct your own research and verify AI-generated reports against primary sources
              before relying on them.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Past Performance</h2>
            <p>
              Past performance, historical scores, and backtest results do <strong>not</strong> guarantee
              future results. Stock markets are inherently unpredictable, and historical patterns may not repeat.
              Any hypothetical or backtested results shown on Divvy are for illustrative purposes only.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Consult a Professional</h2>
            <p>
              Before making any investment decision, you should consult a licensed financial advisor who
              understands your personal financial situation, risk tolerance, and investment objectives.
              Divvy is a data tool — <strong>not a substitute</strong> for professional financial advice.
            </p>
          </section>

          <p className="text-sm text-gray-500 pt-8">
            Last updated: June 12, 2026
          </p>
        </div>

        <nav className="mt-12 pt-6 border-t border-gray-200 dark:border-gray-700 flex justify-center gap-6 text-sm">
          <Link to="/privacy" className="text-gray-500 hover:text-emerald-600 dark:text-gray-400 dark:hover:text-emerald-400">Privacy Policy</Link>
          <Link to="/terms" className="text-gray-500 hover:text-emerald-600 dark:text-gray-400 dark:hover:text-emerald-400">Terms of Service</Link>
        </nav>
      </div>
    </>
  )
}

export default Disclaimer
