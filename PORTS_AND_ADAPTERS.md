# Ports & Adapters -- Communication Between Layers

## The problem

Your domain needs data from the outside world. But if it imports a database
driver, an HTTP client, or a framework, you break the dependency rule:

```
domain ---> infrastructure   FORBIDDEN
```

The domain becomes untestable without a database. You cannot swap
infrastructure without rewriting domain code.

## The solution

The domain defines **what it needs** (the Port). The infrastructure
provides **how it is done** (the Adapter).

```
domain/ports.py          <-- Port (interface, ABC)
infrastructure/adapters.py <-- Adapter (implementation)
```

The domain only knows about the interface. It never knows which
implementation is being used at runtime.

## Anatomy of a Port

A Port is a Python abstract base class (ABC) defined in the domain layer.

```python
# domain/ports.py

from abc import ABC, abstractmethod

class ExchangeRateProvider(ABC):
    """Port -- Provides exchange rates.

    The domain defines this contract. Infrastructure fulfills it.
    """

    @abstractmethod
    def get_rate(self, from_currency: str, to_currency: str) -> float:
        """Return the exchange rate between two currencies.

        Args:
            from_currency: ISO 4217 currency code (e.g., 'EUR').
            to_currency: ISO 4217 currency code (e.g., 'USD').

        Returns:
            The exchange rate as a float.

        Raises:
            CurrencyNotFoundError: If the pair is not available.
        """
        ...
```

### Rules for Ports

1. **Defined in domain.** Never in infrastructure.
2. **Has one responsibility.** If your Port has 10 methods, split it.
3. **Raises domain exceptions only.** `CurrencyNotFoundError`, not `Http404`.
4. **Names a capability, not a technology.** `ExchangeRateProvider`, not `ApiClient`.

### What is a Port?

| Domain needs... | Port name (capability) | NOT (technology) |
|----------------|----------------------|------------------|
| Exchange rates | `ExchangeRateProvider` | `ApiClient` |
| Persistence | `OrderRepository` | `PostgresDatabase` |
| Notifications | `Notifier` | `EmailSender` |
| Current time | `Clock` | `SystemClock` |
| File storage | `FileStorage` | `S3Bucket` |
| Model weights | `WeightProvider` | `HuggingFaceModel` |
| Token batches | `BatchProvider` | `WikiTextDataset` |
| Score persistence | `ScorePersister` | `SafetensorsFile` |

The Port name describes **what the domain needs**, not **how it gets it**.

## Anatomy of an Adapter

An Adapter is a concrete class that implements a Port. It lives in infrastructure.

```python
# infrastructure/adapters.py

from domain.ports import ExchangeRateProvider, CurrencyNotFoundError

class ApiExchangeRateProvider(ExchangeRateProvider):
    """Adapter -- Fetches rates from an external API."""

    def __init__(self, api_key: str, base_url: str = "https://api.example.com"):
        self.api_key = api_key
        self.base_url = base_url

    def get_rate(self, from_currency: str, to_currency: str) -> float:
        response = requests.get(
            f"{self.base_url}/rates",
            params={"from": from_currency, "to": to_currency},
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        if response.status_code == 404:
            raise CurrencyNotFoundError(
                f"No rate for {from_currency} -> {to_currency}"
            )
        return response.json()["rate"]


class FakeExchangeRateProvider(ExchangeRateProvider):
    """Adapter -- Returns hardcoded rates. Used in tests."""

    def __init__(self):
        self._rates = {
            ("EUR", "USD"): 1.10,
            ("USD", "EUR"): 0.91,
        }

    def get_rate(self, from_currency: str, to_currency: str) -> float:
        pair = (from_currency.upper(), to_currency.upper())
        if pair not in self._rates:
            raise CurrencyNotFoundError(
                f"No rate for {from_currency} -> {to_currency}"
            )
        return self._rates[pair]
```

### Rules for Adapters

1. **Must inherit from a domain Port.** Every public adapter class implements an ABC.
2. **Can use any framework.** `requests`, `sqlalchemy`, `boto3`, `torch` -- all allowed.
3. **Translates external errors to domain exceptions.** `Http404` becomes `CurrencyNotFoundError`.
4. **Should have a fake version for tests.** `FakeExchangeRateProvider` is as important
   as `ApiExchangeRateProvider`.

## How the use case uses them

The use case only knows about the Port, never the Adapter:

```python
# application/use_cases.py

class ConvertCurrencyUseCase:
    def __init__(self, rate_provider: ExchangeRateProvider):  # <-- PORT, not adapter
        self.rate_provider = rate_provider

    def execute(self, amount, from_cur, to_cur):
        rate = self.rate_provider.get_rate(from_cur, to_cur)  # <-- calls the port
        ...
```

The orchestration layer decides which adapter to inject:

```python
# orchestration/main.py

# In production:
rate_provider = ApiExchangeRateProvider(api_key="secret")

# In tests:
rate_provider = FakeExchangeRateProvider()

# The use case doesn't care which one it gets:
use_case = ConvertCurrencyUseCase(rate_provider)
```

## Multiple adapters for the same Port

One Port can (and should) have multiple adapters:

```
Port: ExchangeRateProvider
|-- ApiExchangeRateProvider      (production)
|-- DatabaseExchangeRateProvider (cached, faster)
|-- FakeExchangeRateProvider     (unit tests)
|-- LoggingExchangeRateProvider  (debugging wrapper)
```

Swap them without touching domain or application code.

## Testing with Ports & Adapters

```python
# tests/test_application.py

def test_convert_eur_to_usd():
    # Use the fake adapter -- no network, no API key needed
    provider = FakeExchangeRateProvider()
    use_case = ConvertCurrencyUseCase(provider)

    result = use_case.execute(100, "EUR", "USD")

    assert result.converted == 110.0


def test_unknown_currency_raises():
    provider = FakeExchangeRateProvider()
    use_case = ConvertCurrencyUseCase(provider)

    with pytest.raises(CurrencyNotFoundError):
        use_case.execute(100, "EUR", "JPY")
```

## Common mistakes

### Mistake 1: Port in infrastructure

```python
# WRONG -- Port defined in infrastructure
# infrastructure/ports.py
class ExchangeRateProvider(ABC): ...

# Now domain must import infrastructure to use it:
# domain/models.py
from infrastructure.ports import ExchangeRateProvider  # BROKEN DEPENDENCY
```

**Fix:** Move the Port to `domain/ports.py`.

### Mistake 2: Adapter without a Port

```python
# WRONG -- Adapter with no Port
class ApiExchangeRateProvider:  # What contract does this fulfill?
    def get_rate(self, from_cur, to_cur): ...
```

**Fix:** Make it inherit from `domain.ports.ExchangeRateProvider`.

### Mistake 3: Use case bypasses the Port

```python
# WRONG -- Use case calls infrastructure directly
class ConvertCurrencyUseCase:
    def execute(self, amount, from_cur, to_cur):
        response = requests.get("https://api.example.com/rates")  # BYPASSED PORT
        ...
```

**Fix:** Inject a `ExchangeRateProvider` and call its method.

### Mistake 4: Port with too many methods

```python
# WRONG -- God Port
class DataProvider(ABC):
    def get_rate(self, ...): ...
    def save_order(self, ...): ...
    def send_email(self, ...): ...
    def upload_file(self, ...): ...
```

**Fix:** Split into `ExchangeRateProvider`, `OrderRepository`, `Notifier`, `FileStorage`.

## When to create a Port

Create a Port when:

- The domain needs data from outside (API, database, file system)
- The domain needs to trigger a side effect (send email, log, notify)
- The domain needs the current time (so tests can freeze time)
- You want to swap implementations without changing domain code

Do NOT create a Port for:

- Pure functions (these are domain logic, no Port needed)
- Value objects (these are data, not behavior)
- Algorithms (these are domain logic)

## Summary

| Concept | Defined in | Implemented in | Knows about |
|---------|-----------|---------------|-------------|
| Port | `domain/ports.py` | -- | Nothing (it's an interface) |
| Adapter | -- | `infrastructure/adapters.py` | Frameworks + the Port |
| Use Case | `application/` | -- | Only the Port |

The Port is the contract. The Adapter is the fulfillment. The Use Case is the consumer.
