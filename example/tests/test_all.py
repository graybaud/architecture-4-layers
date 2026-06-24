"""Tests for the example application."""

import pytest

from example.domain.models import convert
from example.domain.ports import ExchangeRateProvider, CurrencyNotFoundError
from example.infrastructure.adapters import FakeExchangeRateProvider
from example.application.use_cases import ConvertCurrencyUseCase


# =============================================================================
# Domain tests -- pure unit, no mocks needed
# =============================================================================

class TestConvert:
    def test_simple(self):
        assert convert(100, 1.10) == 110.0

    def test_zero(self):
        assert convert(0, 1.10) == 0.0

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            convert(-100, 1.10)

    def test_rounding(self):
        assert convert(100, 1.105) == 110.50

    def test_large_amount(self):
        assert convert(1_000_000, 1.10) == 1_100_000.0


class TestPort:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            ExchangeRateProvider()


# =============================================================================
# Infrastructure tests -- real adapter, no external deps
# =============================================================================

class TestFakeProvider:
    def test_known_pair(self):
        provider = FakeExchangeRateProvider()
        assert provider.get_rate("EUR", "USD") == 1.10

    def test_case_insensitive(self):
        provider = FakeExchangeRateProvider()
        assert provider.get_rate("eur", "usd") == 1.10

    def test_unknown_pair_raises(self):
        provider = FakeExchangeRateProvider()
        with pytest.raises(CurrencyNotFoundError):
            provider.get_rate("EUR", "JPY")


# =============================================================================
# Application tests -- use case with fake adapter
# =============================================================================

class TestConvertCurrencyUseCase:
    def test_eur_to_usd(self):
        provider = FakeExchangeRateProvider()
        use_case = ConvertCurrencyUseCase(provider)

        result = use_case.execute(100, "EUR", "USD")

        assert result.amount == 100
        assert result.converted == 110.0
        assert result.from_currency == "EUR"
        assert result.to_currency == "USD"

    def test_unknown_currency_propagates_error(self):
        provider = FakeExchangeRateProvider()
        use_case = ConvertCurrencyUseCase(provider)

        with pytest.raises(CurrencyNotFoundError):
            use_case.execute(100, "EUR", "JPY")

    def test_zero_amount(self):
        provider = FakeExchangeRateProvider()
        use_case = ConvertCurrencyUseCase(provider)

        result = use_case.execute(0, "EUR", "USD")

        assert result.converted == 0.0
