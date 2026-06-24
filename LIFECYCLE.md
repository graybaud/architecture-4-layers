# Lifecycle -- Object Creation, Injection, and Destruction

## The rule

> Only the orchestration layer is allowed to create objects that cross
> layer boundaries. Every other layer receives its dependencies through
> its constructor.

This is the single most important rule after the dependency direction.
It prevents hidden coupling and makes every component independently testable.

## Why this matters

Without this rule, objects create their own dependencies:

```python
# WITHOUT the lifecycle rule
class ConvertCurrencyUseCase:
    def execute(self, amount, from_cur, to_cur):
        provider = ApiExchangeRateProvider()  # Created inside
        rate = provider.get_rate(from_cur, to_cur)
        ...
```

Problems:
1. You cannot test `ConvertCurrencyUseCase` without a real API
2. You cannot swap `ApiExchangeRateProvider` for a fake without changing code
3. The use case knows about infrastructure (dependency rule violation)
4. Configuration (API key, URL) leaks into business logic

With the lifecycle rule:

```python
# WITH the lifecycle rule
class ConvertCurrencyUseCase:
    def __init__(self, rate_provider: ExchangeRateProvider):  # Injected
        self.rate_provider = rate_provider

    def execute(self, amount, from_cur, to_cur):
        rate = self.rate_provider.get_rate(from_cur, to_cur)  # Uses injected dep
        ...
```

Now you can test with a fake, swap implementations, and keep configuration out.

## The composition root

The **composition root** is the single place where all objects are created
and wired together. It lives in the orchestration layer.

```python
# orchestration/main.py -- THE COMPOSITION ROOT

def main():
    # 1. Create infrastructure (adapters)
    rate_provider = ApiExchangeRateProvider(api_key=config.API_KEY)
    repository = PostgresOrderRepository(connection_string=config.DB_URL)
    notifier = EmailNotifier(smtp_server=config.SMTP_SERVER)

    # 2. Create application (use cases) with injection
    convert_uc = ConvertCurrencyUseCase(rate_provider)
    create_order_uc = CreateOrderUseCase(repository, notifier)
    pipeline = FullPipeline(convert_uc, create_order_uc)

    # 3. Execute
    result = pipeline.run(args.amount, args.from_cur, args.to_cur)

    # 4. Present
    print(result)
```

### Rules for the composition root

1. **This is the ONLY file with `new`, `Factory`, or DI container calls.**
2. **Should be the only file that imports concrete infrastructure classes.**
3. **Should read configuration (env vars, YAML files, CLI args).**
4. **Should fit on one screen.** If it's > 50 lines, extract a `container.py`.

## What is allowed where

| Layer | Allowed to create | NOT allowed to create |
|-------|-------------------|----------------------|
| `orchestration/` | Everything | Nothing (it's the creator) |
| `application/` | DTOs, dataclasses, lists, dicts | Infrastructure adapters, other use cases |
| `domain/` | Value objects, domain exceptions | Anything from other layers |
| `infrastructure/` | Framework clients (requests.Session, sqlalchemy.Engine) | Use cases, domain objects with behavior |

## Example: object graph for a request

```
orchestration/main.py
  |
  |-- creates --> ApiExchangeRateProvider(api_key)
  |-- creates --> PostgresOrderRepository(db_url)
  |-- creates --> ConvertCurrencyUseCase(provider)
  |                  |
  |                  |-- receives --> ExchangeRateProvider (interface)
  |                  |-- calls --> provider.get_rate()
  |
  |-- creates --> CreateOrderUseCase(repository)
  |                  |
  |                  |-- receives --> OrderRepository (interface)
  |                  |-- calls --> repository.save()
  |
  |-- creates --> FullPipeline(convert_uc, create_order_uc)
  |-- calls --> pipeline.run()
```

Arrows show the direction of both dependency AND creation.
Everything flows downward from orchestration.

## Testing with dependency injection

The lifecycle rule makes testing trivial:

```python
# tests/test_application.py

def test_convert_currency():
    # Create a fake adapter (no API, no network)
    provider = FakeExchangeRateProvider()

    # Inject it into the use case
    use_case = ConvertCurrencyUseCase(provider)

    # Test
    result = use_case.execute(100, "EUR", "USD")
    assert result.converted == 110.0
```

No mocking framework needed. Just pass a fake implementation.

## Common mistakes

### Mistake 1: Creating dependencies inside a method

```python
# WRONG
class ConvertCurrencyUseCase:
    def execute(self, amount, from_cur, to_cur):
        provider = ApiExchangeRateProvider()  # NO
        ...
```

**Fix:** Pass through `__init__`.

### Mistake 2: Use case creating another use case

```python
# WRONG
class FullPipeline:
    def run(self, amount, from_cur, to_cur):
        convert_uc = ConvertCurrencyUseCase(self.provider)  # NO
        ...
```

**Fix:** Both use cases are created in orchestration and injected.

```python
# CORRECT
class FullPipeline:
    def __init__(self, convert_uc: ConvertCurrencyUseCase):
        self.convert_uc = convert_uc  # Injected

    def run(self, amount, from_cur, to_cur):
        return self.convert_uc.execute(amount, from_cur, to_cur)
```

### Mistake 3: Domain creating infrastructure

```python
# WRONG -- domain/models.py
def convert(amount, rate):
    logger = Logger()  # NO -- domain creates infrastructure
    logger.info(f"Converting {amount}")
    return amount * rate
```

**Fix:** If the domain needs logging, define a `Logger` Port and inject it.

### Mistake 4: Infrastructure creating use cases

```python
# WRONG -- infrastructure/adapters.py
class ApiExchangeRateProvider:
    def get_rate(self, from_cur, to_cur):
        if self._cache.is_expired():
            use_case = RefreshCacheUseCase()  # NO
            use_case.execute()
        ...
```

**Fix:** Infrastructure should never know about application layer.
Raise an event or return stale data; let the use case handle cache refresh.

## Singletons and long-lived objects

Some objects should live for the entire application lifetime
(database connection pools, HTTP clients, ML models).

```python
# orchestration/main.py

# Created once, reused across requests
_model = HuggingFaceWeightProvider("phi-2")
_dataset = WikiTextProvider()

def handle_request(amount, from_cur, to_cur):
    use_case = ConvertCurrencyUseCase(_model, _dataset)
    return use_case.execute(amount, from_cur, to_cur)
```

The composition root is the natural place for singletons.
No global variables, no `@singleton` decorators needed.

## Summary

| Principle | Rule |
|-----------|------|
| **Where to create** | Only in `orchestration/` |
| **How to receive** | Through `__init__` parameters |
| **What to inject** | Ports (interfaces), never concrete adapters |
| **Why** | Independent testability, swappable infrastructure, no hidden coupling |
