"""Use cases -- coordinates domain and infrastructure."""

from dataclasses import dataclass

from example.domain.ports import ExchangeRateProvider
from example.domain.models import convert


@dataclass
class ConvertResult:
    """DTO -- returned by ConvertCurrencyUseCase."""
    amount: float
    converted: float
    from_currency: str
    to_currency: str


class ConvertCurrencyUseCase:
    """Converts an amount from one currency to another.

    Coordinates:
    - ExchangeRateProvider (infrastructure) to get the rate
    - convert() (domain) to apply the business rule

    The use case itself contains NO business logic and NO technical details.
    """

    def __init__(self, rate_provider: ExchangeRateProvider):
        self.rate_provider = rate_provider

    def execute(
        self, amount: float, from_currency: str, to_currency: str
    ) -> ConvertResult:
        rate = self.rate_provider.get_rate(from_currency, to_currency)
        converted = convert(amount, rate)
        return ConvertResult(
            amount=amount,
            converted=converted,
            from_currency=from_currency,
            to_currency=to_currency,
        )
