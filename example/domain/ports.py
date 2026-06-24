"""Ports (interfaces) defined by the domain."""

from abc import ABC, abstractmethod


class ExchangeRateProvider(ABC):
    """Port -- Provides exchange rates.

    The domain defines this interface. Infrastructure implements it.
    The domain never knows whether rates come from an API, a database,
    or a hardcoded table. It only calls get_rate().
    """

    @abstractmethod
    def get_rate(self, from_currency: str, to_currency: str) -> float:
        """Return the exchange rate between two currencies.

        Args:
            from_currency: ISO 4217 currency code (e.g., 'EUR').
            to_currency: ISO 4217 currency code (e.g., 'USD').

        Returns:
            The exchange rate as a float (e.g., 1.10 means 1 EUR = 1.10 USD).

        Raises:
            CurrencyNotFoundError: If either currency is not supported.
        """
        ...


class CurrencyNotFoundError(Exception):
    """Raised when a currency pair is not available."""
    pass
