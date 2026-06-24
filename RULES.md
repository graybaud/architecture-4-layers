# The 5 Rules

These rules are the contract. If you follow them, your architecture is correct.
If you break one, you have a leak that will grow over time.

---

## Rule 1 — Four folders, no more

Every project has exactly four top-level directories:

```
orchestration/
application/
domain/
infrastructure/
```

If you have a fifth, either:
- It belongs inside one of the four (e.g., `utils/` → `domain/utils.py`)
- You are mixing concerns (e.g., `models/` with both domain and infrastructure classes)
- You are adding an unnecessary abstraction

### Decision tree: "Where do I put this file?"

```
Does it contain business rules that would still be true
if we changed framework/database/API?
    YES → domain/
    NO  → continue

Does it contain framework-specific code (HTTP, DB, file I/O, GPU)?
    YES → infrastructure/
    NO  → continue

Does it coordinate domain + infrastructure to fulfill a user goal?
    YES → application/
    NO  → continue

Is it a script that starts the application?
    YES → orchestration/
    NO  → You missed something. Re-read the questions.
```

---

## Rule 2 — Dependencies point inward

Imports must follow this direction:

```
orchestration ──→ application ──→ domain ←── infrastructure
```

- `orchestration/` can import from `application/`, `infrastructure/`, and `domain/`
- `application/` can import from `domain/` and from `domain/ports.py` (interfaces)
- `infrastructure/` can import from `domain/ports.py` (to implement interfaces)
- `domain/` can import from the Python standard library, `abc`, and `dataclasses` — **nothing else**

### The dependency rule in one line

```python
# The only import direction that is ALWAYS forbidden:
from infrastructure import anything   # ← NEVER in domain/
from application import anything      # ← NEVER in domain/
from orchestration import anything    # ← NEVER in domain/
```

### Why this matters

If `domain/models.py` imports from `infrastructure/database.py`:
1. You cannot test the domain without a database
2. You cannot swap databases without changing domain code
3. You cannot reuse the domain in a different application

The dependency rule is not about aesthetics. It is about **independent deployability and testability** of your business logic.

---

## Rule 3 — Ports & Adapters for domain ↔ infrastructure

The domain layer defines interfaces (Ports). The infrastructure layer implements them (Adapters).

### The pattern

```python
# domain/ports.py — The PORT (interface)
class ExchangeRateProvider(ABC):
    @abstractmethod
    def get_rate(self, from_cur: str, to_cur: str) -> float: ...

# infrastructure/adapters.py — The ADAPTER (implementation)
class ApiExchangeRateProvider(ExchangeRateProvider):
    def get_rate(self, from_cur: str, to_cur: str) -> float:
        response = requests.get(f"https://api.example.com/rates/{from_cur}/{to_cur}")
        return response.json()["rate"]

class FakeExchangeRateProvider(ExchangeRateProvider):
    def get_rate(self, from_cur: str, to_cur: str) -> float:
        return 1.10  # Hardcoded for tests
```

### The rule

- The domain defines **what** it needs (the Port)
- The infrastructure provides **how** it is done (the Adapter)
- The domain never knows which adapter is being used
- You can swap adapters without touching domain or application code

### What counts as a Port?

Anything where the domain needs data or services from the outside world:

| Domain needs... | Port name | Example adapters |
|----------------|-----------|-----------------|
| Exchange rates | `ExchangeRateProvider` | `ApiRateProvider`, `DatabaseRateProvider`, `FakeRateProvider` |
| Persistence | `Repository` | `PostgresRepository`, `InMemoryRepository` |
| Notifications | `Notifier` | `EmailNotifier`, `SmsNotifier`, `LogNotifier` |
| Current time | `Clock` | `SystemClock`, `FrozenClock` (for tests) |
| File storage | `FileStorage` | `S3FileStorage`, `LocalFileStorage` |

### What is NOT a Port?

- Pure functions (these belong in `domain/models.py`)
- Algorithms (these belong in `domain/algorithms.py`)
- Value objects (these belong in `domain/models.py`)

---

## Rule 4 — Only orchestration creates objects

The composition root (where `new`, `Factory`, or dependency injection containers are called) must be in the `orchestration/` layer. No other layer is allowed to instantiate objects that cross layer boundaries.

### Allowed and forbidden

```python
# ✅ ALLOWED — orchestration/main.py
rate_provider = ApiExchangeRateProvider()        # Creating infrastructure
use_case = ConvertCurrencyUseCase(rate_provider) # Creating application
result = use_case.execute(100, "EUR", "USD")     # Executing

# ❌ FORBIDDEN — application/use_cases.py
class ConvertCurrencyUseCase:
    def execute(self, amount, from_cur, to_cur):
        provider = ApiExchangeRateProvider()  # NO — creating inside use case
        ...

# ❌ FORBIDDEN — domain/models.py
def convert(amount, rate):
    logger = Logger()  # NO — creating infrastructure from domain
    ...

# ❌ FORBIDDEN — infrastructure/adapters.py
class ApiExchangeRateProvider:
    def __init__(self):
        self.use_case = ConvertCurrencyUseCase(self)  # NO — creating application from infrastructure
```

### Exception: objects that do not cross layer boundaries

Creating a `list`, `dict`, `dataclass`, or any pure data structure is always allowed anywhere. The rule applies to **objects that have behavior and belong to a specific layer**.

```python
# ✅ ALLOWED anywhere
result = ConvertResult(amount=100, converted=110.0, from_currency="EUR", to_currency="USD")
items = []
config = {"timeout": 30}
```

---

## Rule 5 — Test complexity grows with distance from domain

| Layer | Test type | Dependencies | Speed | Example |
|-------|-----------|-------------|-------|---------|
| `domain/` | Unit | None | < 0.1s | `test_convert()` |
| `infrastructure/` | Unit + mock | `tmp_path`, mocks | < 0.5s | `test_json_persister(tmp_path)` |
| `application/` | Unit + fake | Fake adapters | < 0.5s | `test_use_case_with_fake_provider()` |
| `orchestration/` | Integration | Real adapters | > 1s | `test_cli_end_to_end()` |

### The rule

If your domain tests need a database, a GPU, or a network connection, **you have broken Rule 2** (dependencies point inward). The domain should be testable with nothing but `pytest` and plain Python objects.

### Test count expectation

For a healthy project:
- 60-70% of tests should be in `domain/` (unit tests, fast, many edge cases)
- 20-25% in `application/` (use case tests with fakes)
- 10-15% in `infrastructure/` (adapter tests with mocks or real services)
- < 5% in `orchestration/` (integration tests, slow, few happy paths)

### Example test structure

```
tests/
├── unit/
│   ├── test_domain.py        # 60% of tests — pure business logic
│   ├── test_application.py   # 20% of tests — use cases with fakes
│   └── test_infrastructure.py # 10% of tests — adapters with mocks
├── integration/
│   └── test_orchestration.py  # 10% of tests — end-to-end
└── e2e/
    └── test_cli.py            # < 5% — full system
```

---

## Quick compliance check

Ask yourself these 5 questions. If all answers are "yes", your architecture is correct.

| # | Question | Rule |
|---|----------|------|
| 1 | Do I have exactly 4 top-level directories? | Rule 1 |
| 2 | Can I delete `infrastructure/`, `application/`, and `orchestration/` and still run `domain/` tests? | Rule 2 |
| 3 | Does every public class in `infrastructure/` implement an interface from `domain/`? | Rule 3 |
| 4 | Does `new` or any factory call exist ONLY in `orchestration/`? | Rule 4 |
| 5 | Can I run all domain tests in under 1 second? | Rule 5 |
