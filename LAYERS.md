# The 4 Layers — Detailed Reference

## Overview

Every project built with this architecture contains exactly four top-level directories:
orchestration/ Who starts what, and when?
application/ What use case is being executed?
domain/ What is true, always? (pure business rules)
infrastructure/ How is it done? (technical adapters)


Each layer has a single responsibility. If you cannot describe what a file does in one sentence using the words from its layer's question, it is in the wrong place.

---

## 1. Domain — "What is true, always?"

### Definition

The domain layer contains **pure business logic**. It is the heart of your application. It knows nothing about databases, HTTP, files, GPUs, or frameworks. It would still compile and pass its tests if you deleted every other directory.

### What goes here

| Category | Examples | File name convention |
|----------|----------|---------------------|
| Business rules | `convert(amount, rate) -> float` | `models.py` |
| Value objects | `Money(amount, currency)` | `models.py` |
| Algorithms | `otsu_threshold(scores) -> float` | `algorithms.py` |
| Domain services | `transfer_funds(from_acc, to_acc, amount)` | `services.py` |
| Ports (interfaces) | `class ExchangeRateProvider(ABC)` | `ports.py` |
| Constants | `MAX_WITHDRAWAL = 5000` | `constants.py` |

### What does NOT go here

- Database queries (→ infrastructure)
- HTTP requests (→ infrastructure)
- File I/O (→ infrastructure)
- Framework-specific code (→ infrastructure)
- CLI argument parsing (→ orchestration)
- Use case coordination (→ application)

### Rules

1. **Zero framework imports.** No `django`, `flask`, `sqlalchemy`, `torch.nn`, `transformers`, `datasets`.
2. **Only standard library + abstract base classes.** `from abc import ABC, abstractmethod` is allowed. `import math` is allowed.
3. **100% unit testable without mocks.** Every function in this layer must be testable with plain Python objects.
4. **No side effects.** Functions return values. They do not write to files, call APIs, or mutate global state (except through well-defined domain objects).

### Example — Pure business rule

```python
# domain/models.py

def convert(amount: float, rate: float) -> float:
    """Convert an amount from one currency to another.

    Args:
        amount: The amount to convert. Must be non-negative.
        rate: The exchange rate (multiplier).

    Returns:
        The converted amount, rounded to 2 decimal places.

    Raises:
        ValueError: If amount is negative.
    """
    if amount < 0:
        raise ValueError(f"Amount must be non-negative, got {amount}")
    return round(amount * rate, 2)
```

Example — Port (interface)
```python
# domain/ports.py

from abc import ABC, abstractmethod

class ExchangeRateProvider(ABC):
    """Port — Provides exchange rates.

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
```

Anti-patterns (what NOT to do)
```python
# ❌ WRONG — domain imports infrastructure
from infrastructure.database import get_rates  # NEVER

# ❌ WRONG — domain knows about frameworks
from transformers import AutoModel  # NEVER

# ❌ WRONG — domain does I/O
def get_rate(from_cur, to_cur):
    response = requests.get(f"https://api.example.com/rates")  # NEVER
    return response.json()["rate"]

# ❌ WRONG — domain orchestrates
def main():
    rate_provider = ApiRateProvider()
    result = ConvertCurrencyUseCase(rate_provider).execute(100, "EUR", "USD")
    print(result)
```

How to test
```python
# tests/test_domain.py

def test_convert_simple():
    assert convert(100, 1.10) == 110.0

def test_convert_zero():
    assert convert(0, 1.10) == 0.0

def test_convert_negative_raises():
    with pytest.raises(ValueError, match="non-negative"):
        convert(-100, 1.10)

def test_port_is_abstract():
    with pytest.raises(TypeError):
        ExchangeRateProvider()  # Cannot instantiate an ABC
```

2. Infrastructure — "How is it done?"

**Definition**

The infrastructure layer contains technical adapters. Each adapter implements a Port (interface) defined in the domain layer. This is where frameworks, databases, and external services live.

What goes here
Category    Examples    File name convention
Database adapters   PostgresExchangeRateProvider    database.py
HTTP adapters   ApiExchangeRateProvider http_client.py
Framework adapters  HuggingFaceWeightProvider   models.py
File I/O    JsonScorePersister  persistence.py
Hooks/Collectors    ActivationCollector hooks.py
What does NOT go here
Business logic (→ domain)

Use case coordination (→ application)

CLI entry points (→ orchestration)

Rules
Must implement a Port from the domain. Every public class in infrastructure should inherit from an ABC defined in domain/ports.py.

Can import frameworks. django, sqlalchemy, transformers, requests, torch are all allowed here.

Can have side effects. Database writes, HTTP calls, file I/O are expected.

Should be replaceable. You should be able to swap a Postgres adapter for a SQLite adapter without changing any other layer.

Example — Adapter implementing a Port
```python
# infrastructure/adapters.py

from domain.ports import ExchangeRateProvider, CurrencyNotFoundError

class FakeExchangeRateProvider(ExchangeRateProvider):
    """Adapter — Uses a hardcoded table of rates.

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
```

Anti-patterns
```python
# ❌ WRONG — adapter contains business logic
class ExchangeRateProvider:
    def get_rate(self, from_cur, to_cur):
        rate = self._fetch_from_api()
        # Business logic should be in domain, not here
        if rate > 2.0:
            raise ValueError("Rate too high")  # This is a domain rule
        return rate

# ❌ WRONG — adapter does not implement a domain Port
class RandomUtility:  # What port does this implement?
    def do_something(self): ...
```

3. Application — "What use case?"

Definition

The application layer coordinates domain logic and infrastructure to fulfill a specific user goal. It contains no business rules (those are in domain) and no technical details (those are in infrastructure). It is the conductor, not the musician.

What goes here
Category    Examples    File name convention
Use cases   ConvertCurrencyUseCase  use_cases.py
Input/Output DTOs   ConvertResult   dtos.py
Pipelines   FullPipeline (multi-step)   pipeline.py
Unit of Work    UnitOfWork (transaction boundary)   uow.py
What does NOT go here
Business rules (→ domain)

Database queries (→ infrastructure, called through a Port)

CLI parsing (→ orchestration)

Rules
Receives everything through the constructor. Dependencies are injected, never imported or created.

Has exactly one public method. Typically execute(). If you need more, you probably need another use case.

Contains no if statements about business rules. Business decisions are delegated to the domain.

Returns a DTO (data transfer object). The result is a simple dataclass, not a domain entity with behavior.

Example
```python
# application/use_cases.py

from dataclasses import dataclass
from domain.ports import ExchangeRateProvider
from domain.models import convert


@dataclass
class ConvertResult:
    """DTO — returned by ConvertCurrencyUseCase."""
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
        # Dependency injected — the use case does not know or care
        # whether the provider is fake, API-based, or database-backed.
        self.rate_provider = rate_provider

    def execute(
        self, amount: float, from_currency: str, to_currency: str
    ) -> ConvertResult:
        # 1. Get data from infrastructure (through the port)
        rate = self.rate_provider.get_rate(from_currency, to_currency)

        # 2. Apply domain logic
        converted = convert(amount, rate)

        # 3. Return a DTO
        return ConvertResult(
            amount=amount,
            converted=converted,
            from_currency=from_currency,
            to_currency=to_currency,
        )
```

Anti-patterns
```python
# ❌ WRONG — use case creates its own dependencies
class ConvertCurrencyUseCase:
    def execute(self, amount, from_cur, to_cur):
        provider = ApiExchangeRateProvider()  # NEVER create here
        rate = provider.get_rate(from_cur, to_cur)
        ...

# ❌ WRONG — use case contains business logic
class ConvertCurrencyUseCase:
    def execute(self, amount, from_cur, to_cur):
        rate = provider.get_rate(from_cur, to_cur)
        if rate > 2.0:  # This is domain logic, should be in domain/models.py
            raise ValueError("Rate too high")
        ...

# ❌ WRONG — use case returns a domain entity
class ConvertCurrencyUseCase:
    def execute(self, ...) -> Money:  # Return a DTO, not a domain object
        ...
```

4. Orchestration — "Who starts what, and when?"

Definition

The orchestration layer is the entry point of your application. Its only job is to create objects and call the first use case. It contains no business logic, no technical details, and no coordination logic (that is in the application layer).

What goes here
Category    Examples    File name convention
CLI entry point main.py, cli.py main.py
Web route handlers  routes.py (thin, delegates to use cases)    routes.py
Dependency injection    Composition root    container.py
Configuration   Loading YAML/ENV files  config.py
What does NOT go here
Business logic (→ domain)

Use case coordination (→ application)

Technical adapters (→ infrastructure)

Rules
This is the ONLY place where new or factory calls happen. Every object is created here and injected downward.

Should fit in one screen. If your main() is longer than 50 lines, something is wrong.

Contains no if statements about what to do. Only if about configuration (e.g., if args.verbose: print(...)).

Example
```python
# orchestration/main.py

from infrastructure.adapters import FakeExchangeRateProvider
from application.use_cases import ConvertCurrencyUseCase


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
```

Anti-patterns
```python
# ❌ WRONG — orchestration contains business logic
def main():
    amount = float(input("Amount: "))
    if amount < 0:  # This is domain logic
        print("Must be positive")
        return
    ...

# ❌ WRONG — orchestration coordinates multiple steps
def main():
    provider = ApiRateProvider()
    rate = provider.get_rate("EUR", "USD")
    converted = amount * rate  # Domain logic
    Database().save(converted)  # Infrastructure called directly
    Email().send(converted)     # Multiple use cases in one place
    ...

# ✅ CORRECT — delegate to use case
def main():
    provider = ApiRateProvider()
    use_case = ConvertCurrencyUseCase(provider)
    result = use_case.execute(100, "EUR", "USD")
    print(result)
```

Summary Table

Question    Layer   Key Rule    Test Speed
What is true?   domain/ Zero framework imports  < 1s
How is it done? infrastructure/ Must implement a domain Port    < 1s (with mocks)
What use case?  application/    Dependencies injected via constructor   < 1s (with fakes)
Who starts what?    orchestration/  Only place with new Seconds (integration)
ENDOFFILE














Le problème vient du heredoc : les backticks ``` à l'intérieur du contenu ferment prématurément le `<< 'ENDOFFILE'`. On utilise `cat` avec un fichier temporaire écrit par Python pour éviter ça :

```bash
python << 'PYEOF'
content = r'''# The 4 Layers — Detailed Reference

## Overview

Every project built with this architecture contains exactly four top-level directories:

```
orchestration/    Who starts what, and when?
application/      What use case is being executed?
domain/           What is true, always? (pure business rules)
infrastructure/   How is it done? (technical adapters)
```

Each layer has a single responsibility. If you cannot describe what a file does
in one sentence using the words from its layer's question, it is in the wrong place.

---

## 1. Domain — "What is true, always?"

### Definition

The domain layer contains **pure business logic**. It is the heart of your application.
It knows nothing about databases, HTTP, files, GPUs, or frameworks. It would still
compile and pass its tests if you deleted every other directory.

### What goes here

| Category | Examples | File name convention |
|----------|----------|---------------------|
| Business rules | `convert(amount, rate) -> float` | `models.py` |
| Value objects | `Money(amount, currency)` | `models.py` |
| Algorithms | `otsu_threshold(scores) -> float` | `algorithms.py` |
| Domain services | `transfer_funds(from_acc, to_acc, amount)` | `services.py` |
| Ports (interfaces) | `class ExchangeRateProvider(ABC)` | `ports.py` |
| Constants | `MAX_WITHDRAWAL = 5000` | `constants.py` |

### What does NOT go here

- Database queries (→ infrastructure)
- HTTP requests (→ infrastructure)
- File I/O (→ infrastructure)
- Framework-specific code (→ infrastructure)
- CLI argument parsing (→ orchestration)
- Use case coordination (→ application)

### Rules

1. **Zero framework imports.** No `django`, `flask`, `sqlalchemy`, `torch.nn`, `transformers`, `datasets`.
2. **Only standard library + abstract base classes.** `from abc import ABC, abstractmethod` is allowed. `import math` is allowed.
3. **100% unit testable without mocks.** Every function in this layer must be testable with plain Python objects.
4. **No side effects.** Functions return values. They do not write to files, call APIs, or mutate global state.

### Example — Pure business rule

```python
# domain/models.py

def convert(amount: float, rate: float) -> float:
    """Convert an amount from one currency to another.

    Args:
        amount: The amount to convert. Must be non-negative.
        rate: The exchange rate (multiplier).

    Returns:
        The converted amount, rounded to 2 decimal places.

    Raises:
        ValueError: If amount is negative.
    """
    if amount < 0:
        raise ValueError(f"Amount must be non-negative, got {amount}")
    return round(amount * rate, 2)
```

### Example — Port (interface)

```python
# domain/ports.py

from abc import ABC, abstractmethod

class ExchangeRateProvider(ABC):
    """Port — Provides exchange rates.

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
```

### Anti-patterns (what NOT to do)

```python
# ❌ WRONG — domain imports infrastructure
from infrastructure.database import get_rates  # NEVER

# ❌ WRONG — domain knows about frameworks
from transformers import AutoModel  # NEVER

# ❌ WRONG — domain does I/O
def get_rate(from_cur, to_cur):
    response = requests.get(f"https://api.example.com/rates")  # NEVER
    return response.json()["rate"]

# ❌ WRONG — domain orchestrates
def main():
    rate_provider = ApiRateProvider()
    result = ConvertCurrencyUseCase(rate_provider).execute(100, "EUR", "USD")
    print(result)
```

### How to test

```python
# tests/test_domain.py

def test_convert_simple():
    assert convert(100, 1.10) == 110.0

def test_convert_zero():
    assert convert(0, 1.10) == 0.0

def test_convert_negative_raises():
    with pytest.raises(ValueError, match="non-negative"):
        convert(-100, 1.10)

def test_port_is_abstract():
    with pytest.raises(TypeError):
        ExchangeRateProvider()  # Cannot instantiate an ABC
```

---

## 2. Infrastructure — "How is it done?"

### Definition

The infrastructure layer contains **technical adapters**. Each adapter implements
a Port (interface) defined in the domain layer. This is where frameworks, databases,
and external services live.

### What goes here

| Category | Examples | File name convention |
|----------|----------|---------------------|
| Database adapters | `PostgresExchangeRateProvider` | `database.py` |
| HTTP adapters | `ApiExchangeRateProvider` | `http_client.py` |
| Framework adapters | `HuggingFaceWeightProvider` | `models.py` |
| File I/O | `JsonScorePersister` | `persistence.py` |
| Hooks/Collectors | `ActivationCollector` | `hooks.py` |

### What does NOT go here

- Business logic (→ domain)
- Use case coordination (→ application)
- CLI entry points (→ orchestration)

### Rules

1. **Must implement a Port from the domain.** Every public class in infrastructure
   should inherit from an ABC defined in `domain/ports.py`.
2. **Can import frameworks.** `django`, `sqlalchemy`, `transformers`, `requests`,
   `torch` are all allowed here.
3. **Can have side effects.** Database writes, HTTP calls, file I/O are expected.
4. **Should be replaceable.** You should be able to swap a Postgres adapter for
   a SQLite adapter without changing any other layer.

### Example — Adapter implementing a Port

```python
# infrastructure/adapters.py

from domain.ports import ExchangeRateProvider, CurrencyNotFoundError

class FakeExchangeRateProvider(ExchangeRateProvider):
    """Adapter — Uses a hardcoded table of rates.

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
```

### Anti-patterns

```python
# ❌ WRONG — adapter contains business logic
class ExchangeRateProvider:
    def get_rate(self, from_cur, to_cur):
        rate = self._fetch_from_api()
        if rate > 2.0:
            raise ValueError("Rate too high")  # This is a domain rule
        return rate

# ❌ WRONG — adapter does not implement a domain Port
class RandomUtility:  # What port does this implement?
    def do_something(self): ...
```

---

## 3. Application — "What use case?"

### Definition

The application layer coordinates domain logic and infrastructure to fulfill a
specific user goal. It contains **no business rules** (those are in domain) and
**no technical details** (those are in infrastructure). It is the conductor, not the musician.

### What goes here

| Category | Examples | File name convention |
|----------|----------|---------------------|
| Use cases | `ConvertCurrencyUseCase` | `use_cases.py` |
| Input/Output DTOs | `ConvertResult` | `dtos.py` |
| Pipelines | `FullPipeline` (multi-step) | `pipeline.py` |
| Unit of Work | `UnitOfWork` (transaction boundary) | `uow.py` |

### What does NOT go here

- Business rules (→ domain)
- Database queries (→ infrastructure, called through a Port)
- CLI parsing (→ orchestration)

### Rules

1. **Receives everything through the constructor.** Dependencies are injected,
   never imported or created.
2. **Has exactly one public method.** Typically `execute()`. If you need more,
   you probably need another use case.
3. **Contains no `if` statements about business rules.** Business decisions
   are delegated to the domain.
4. **Returns a DTO (data transfer object).** The result is a simple dataclass,
   not a domain entity with behavior.

### Example

```python
# application/use_cases.py

from dataclasses import dataclass
from domain.ports import ExchangeRateProvider
from domain.models import convert


@dataclass
class ConvertResult:
    """DTO — returned by ConvertCurrencyUseCase."""
    amount: float
    converted: float
    from_currency: str
    to_currency: str


class ConvertCurrencyUseCase:
    """Converts an amount from one currency to another.

    Coordinates:
    - ExchangeRateProvider (infrastructure) to get the rate
    - convert() (domain) to apply the business rule
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
```

### Anti-patterns

```python
# ❌ WRONG — use case creates its own dependencies
class ConvertCurrencyUseCase:
    def execute(self, amount, from_cur, to_cur):
        provider = ApiExchangeRateProvider()  # NEVER create here
        ...

# ❌ WRONG — use case contains business logic
class ConvertCurrencyUseCase:
    def execute(self, amount, from_cur, to_cur):
        rate = provider.get_rate(from_cur, to_cur)
        if rate > 2.0:  # This is domain logic
            raise ValueError("Rate too high")
        ...

# ❌ WRONG — use case returns a domain entity
class ConvertCurrencyUseCase:
    def execute(self, ...) -> Money:  # Return a DTO, not a domain object
        ...
```

---

## 4. Orchestration — "Who starts what, and when?"

### Definition

The orchestration layer is the entry point of your application. Its **only** job
is to create objects and call the first use case. It contains no business logic,
no technical details, and no coordination logic (that is in the application layer).

### What goes here

| Category | Examples | File name convention |
|----------|----------|---------------------|
| CLI entry point | `main.py`, `cli.py` | `main.py` |
| Web route handlers | `routes.py` (thin, delegates to use cases) | `routes.py` |
| Dependency injection | Composition root | `container.py` |
| Configuration | Loading YAML/ENV files | `config.py` |

### What does NOT go here

- Business logic (→ domain)
- Use case coordination (→ application)
- Technical adapters (→ infrastructure)

### Rules

1. **This is the ONLY place where `new` or factory calls happen.**
   Every object is created here and injected downward.
2. **Should fit in one screen.** If your `main()` is longer than 50 lines,
   something is wrong.
3. **Contains no `if` statements about what to do.** Only `if` about
   configuration (e.g., `if args.verbose: print(...)`).

### Example

```python
# orchestration/main.py

from infrastructure.adapters import FakeExchangeRateProvider
from application.use_cases import ConvertCurrencyUseCase


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
```

### Anti-patterns

```python
# ❌ WRONG — orchestration contains business logic
def main():
    amount = float(input("Amount: "))
    if amount < 0:  # This is domain logic
        print("Must be positive")
        return
    ...

# ❌ WRONG — orchestration coordinates multiple steps
def main():
    provider = ApiRateProvider()
    rate = provider.get_rate("EUR", "USD")
    converted = amount * rate  # Domain logic
    Database().save(converted)  # Infrastructure called directly
    Email().send(converted)     # Multiple use cases in one place
    ...

# ✅ CORRECT — delegate to use case
def main():
    provider = ApiRateProvider()
    use_case = ConvertCurrencyUseCase(provider)
    result = use_case.execute(100, "EUR", "USD")
    print(result)
```

---

## Summary Table

| Question | Layer | Key Rule | Test Speed |
|----------|-------|----------|------------|
| What is true? | `domain/` | Zero framework imports | < 1s |
| How is it done? | `infrastructure/` | Must implement a domain Port | < 1s (with mocks) |
| What use case? | `application/` | Dependencies injected via constructor | < 1s (with fakes) |
| Who starts what? | `orchestration/` | Only place with `new` | Seconds (integration) |