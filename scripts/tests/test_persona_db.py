"""Tests for scripts/persona_db.py — ticker mapping functions."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # scripts/tests/../../ = divvy/
sys.path.insert(0, str(ROOT / "scripts"))


class TestShortToTicker:
    """Tests for short_to_ticker() — short code to ticker conversion."""

    def test_known_mapping_maybank(self):
        """MAYBANK → 1155.KL."""
        from persona_db import short_to_ticker

        assert short_to_ticker("MAYBANK") == "1155.KL"

    def test_known_mapping_axreit(self):
        """AXREIT → 5106.KL."""
        from persona_db import short_to_ticker

        assert short_to_ticker("AXREIT") == "5106.KL"

    def test_known_mapping_inta(self):
        """INTA → INTA.KL (non-numeric code)."""
        from persona_db import short_to_ticker

        assert short_to_ticker("INTA") == "INTA.KL"

    def test_unknown_fallback(self):
        """Unknown short code appends .KL suffix."""
        from persona_db import short_to_ticker

        assert short_to_ticker("UNKNOWN") == "UNKNOWN.KL"

    def test_unknown_numeric_fallback(self):
        """Unknown numeric code also gets .KL suffix."""
        from persona_db import short_to_ticker

        assert short_to_ticker("9999") == "9999.KL"

    def test_all_known_mappings_end_with_kl(self):
        """All 24 known ticker mappings end with .KL."""
        from persona_db import SHORT_TO_TICKER

        for short, ticker in SHORT_TO_TICKER.items():
            assert ticker.endswith(".KL"), f"{short} -> {ticker} should end with .KL"

    def test_sem_mapping(self):
        """SEM → 5250.KL (was missing, caused FK violations)."""
        from persona_db import short_to_ticker

        assert short_to_ticker("SEM") == "5250.KL"


class TestTickerToShort:
    """Tests for ticker_to_short() — ticker to short code conversion."""

    def test_known_reverse_mapping(self):
        """1155.KL → MAYBANK."""
        from persona_db import ticker_to_short

        assert ticker_to_short("1155.KL") == "MAYBANK"

    def test_known_reverse_inta(self):
        """INTA.KL → INTA."""
        from persona_db import ticker_to_short

        assert ticker_to_short("INTA.KL") == "INTA"

    def test_unknown_ticker_strips_kl(self):
        """Unknown ticker strips .KL suffix."""
        from persona_db import ticker_to_short

        assert ticker_to_short("9999.KL") == "9999"

    def test_ticker_without_kl_stays_unchanged(self):
        """Ticker without .KL suffix is returned as-is."""
        from persona_db import ticker_to_short

        assert ticker_to_short("AAPL") == "AAPL"

    def test_roundtrip_all_known(self):
        """short_to_ticker(ticker_to_short(x)) == x for all known tickers."""
        from persona_db import short_to_ticker, ticker_to_short, SHORT_TO_TICKER

        for ticker in SHORT_TO_TICKER.values():
            short = ticker_to_short(ticker)
            back = short_to_ticker(short)
            assert back == ticker, f"Roundtrip failed: {ticker} -> {short} -> {back}"

    def test_reverse_roundtrip_all_known(self):
        """ticker_to_short(short_to_ticker(x)) == x for all known short codes."""
        from persona_db import short_to_ticker, ticker_to_short, SHORT_TO_TICKER

        for short in SHORT_TO_TICKER:
            ticker = short_to_ticker(short)
            back = ticker_to_short(ticker)
            assert back == short, f"Reverse roundtrip failed: {short} -> {ticker} -> {back}"


class TestTickerMaps:
    """Tests for SHORT_TO_TICKER and TICKER_TO_SHORT dicts."""

    def test_bidirectional_consistency(self):
        """TICKER_TO_SHORT is the exact inverse of SHORT_TO_TICKER."""
        from persona_db import SHORT_TO_TICKER, TICKER_TO_SHORT

        # Same number of entries
        assert len(TICKER_TO_SHORT) == len(SHORT_TO_TICKER)

        # Every value in SHORT_TO_TICKER is a key in TICKER_TO_SHORT
        for ticker in SHORT_TO_TICKER.values():
            assert ticker in TICKER_TO_SHORT

        # Every key in TICKER_TO_SHORT maps back to the correct short code
        for short, ticker in SHORT_TO_TICKER.items():
            assert TICKER_TO_SHORT[ticker] == short

    def test_no_duplicate_tickers(self):
        """No two short codes map to the same ticker (FK constraint protection)."""
        from persona_db import SHORT_TO_TICKER

        tickers = list(SHORT_TO_TICKER.values())
        assert len(tickers) == len(set(tickers)), "Duplicate ticker found"

    def test_count(self):
        """Verify we have the expected number of mappings (25 stocks)."""
        from persona_db import SHORT_TO_TICKER

        assert len(SHORT_TO_TICKER) == 26
