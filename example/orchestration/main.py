"""Entry point -- composition root."""

from example.infrastructure.adapters import FakeExchangeRateProvider
from example.application.use_cases import ConvertCurrencyUseCase


def main():
    # 1. Create infrastructure (adapters)
    rate_provider = FakeExchangeRateProvider()

    # 2. Create application (use case) with injection
    use_case = ConvertCurrencyUseCase(rate_provider)

    # 3. Execute
    result = use_case.execute(100, "EUR", "USD")

    # 4. Present result
    print(
        f"{result.amount:.2f} {result.from_currency} = "
        f"{result.converted:.2f} {result.to_currency}"
    )


if __name__ == "__main__":
    main()
