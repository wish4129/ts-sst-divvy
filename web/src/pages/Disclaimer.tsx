import React from 'react'

const Disclaimer: React.FC = () => {
  return (
    <div className="max-w-3xl mx-auto py-12 px-4">
      <h1 className="text-3xl font-bold mb-8">Disclaimer</h1>

      <div className="prose prose-lg dark:prose-invert space-y-6">
        <section>
          <h2 className="text-xl font-semibold mb-3">No Financial Advice</h2>
          <p>
            Divvy provides stock analysis, scores, and forecasts for informational and educational purposes only.
            Nothing on this platform constitutes financial advice, investment recommendations, or solicitation
            to buy or sell any security.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">No Liability</h2>
          <p>
            Divvy and its creators <strong>do not accept any liability</strong> for any financial loss,
            profit loss, or damages arising from the use of information, reports, forecasts, or analysis
            provided on this platform. All investment decisions are made at your own risk.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">Data Accuracy</h2>
          <p>
            Stock data is sourced from third-party providers (yfinance, Bursa Malaysia public data) and
            may contain errors, delays, or omissions. Divvy does not guarantee the accuracy, completeness,
            or timeliness of any data displayed.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">AI-Generated Reports</h2>
          <p>
            Some analysis reports and forecasts are AI-generated. These are statistical models — not human
            financial analysis. They may contain factual errors or flawed reasoning. Always conduct your
            own research before making investment decisions.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">Past Performance</h2>
          <p>
            Past performance and historical scores do not guarantee future results. Stock markets are
            inherently unpredictable. Any backtest results shown are hypothetical.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">Consult a Professional</h2>
          <p>
            You should consult a licensed financial advisor before making any investment decisions.
            Divvy is a tool — not a substitute for professional advice.
          </p>
        </section>

        <p className="text-sm text-gray-500 pt-8">
          Last updated: June 11, 2026
        </p>
      </div>
    </div>
  )
}

export default Disclaimer
