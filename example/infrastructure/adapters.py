""""""

from example.domain.ports import ExchangeRateProvider, CurrencyNotFoundError


class FakeExchangeRateProvider(ExchangeRateProvider):
    """Adapter -- Uses a hardcoded table of rates.

    Useful for tests and development. Replace with ApiExchangeRateProvider
    in production without changing any other code.
    """

    def __init__(self):
        self._rates = {
            ("EUR", "USD"): 1.10,
            ("USD", "EUR"): 0.91,
            ("EUR", "GBP"): 0.85,
        }

    def get_rate(self, from_currency: str, to_currency: str) -> float:
        pair = (from_currency.upper(), to_currency.upper())
        if pair not in self._rates:
            raise CurrencyNotFoundError(
                f"No rate available for {from_currency} -> {to_currency}"
            )
        return self._rates[pair]
