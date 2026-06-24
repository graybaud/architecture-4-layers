# FAQ -- Where Do I Put X?

## Files and folders

### Where do I put utility functions?

**If they are pure and have no framework dependencies:** `domain/`

```python
# domain/validation.py
def validate_email(email: str) -> bool: ...
def validate_amount(amount: float) -> None: ...
```

**If they depend on a framework:** `infrastructure/`

```python
# infrastructure/logging.py
def setup_logger(level: str) -> logging.Logger: ...
```

### Where do I put constants?

**If they are business constants:** `domain/constants.py`

```python
MAX_WITHDRAWAL = 5000
SUPPORTED_CURRENCIES = ["EUR", "USD", "GBP"]
```

**If they are technical constants:** `infrastructure/config.py` or `orchestration/config.py`

```python
DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
```

### Where do I put configuration?

`orchestration/config.py` or `orchestration/config.yaml`

```python
# orchestration/config.py
import os

API_KEY = os.getenv("API_KEY", "default")
DB_URL = os.getenv("DB_URL", "sqlite:///local.db")
```

Configuration is an orchestration concern. It wires the application together.
It should never be imported by domain or application code.

### Where do I put database models?

**If using SQLAlchemy/ORM:** `infrastructure/persistence/models.py`

These are technical details. The domain should not know about tables,
columns, or foreign keys. The domain works with pure Python objects.

```python
# infrastructure/persistence/models.py
class OrderModel(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    amount = Column(Float)
```

### Where do I put the domain entities?

`domain/models.py`

```python
# domain/models.py
@dataclass
class Order:
    id: str
    amount: float
    currency: str

    def is_large(self) -> bool:
        return self.amount > 10000
```

The infrastructure adapter converts between ORM models and domain entities.

### Where do I put regular expressions?

**If they validate business rules:** `domain/validation.py`

```python
IBAN_PATTERN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$")
```

**If they parse technical formats:** `infrastructure/parsers.py`

```python
LOG_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2}) (.*)$")
```

### Where do I put CLI argument parsing?

`orchestration/cli.py`

```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--amount", type=float, required=True)
    return parser.parse_args()
```

The orchestration layer parses arguments and passes them to the use case.
The use case never sees `argparse`.

### Where do I put HTTP route handlers?

`orchestration/routes.py`

```python
# orchestration/routes.py
@app.post("/convert")
def convert_endpoint(request: ConvertRequest):
    use_case = ConvertCurrencyUseCase(provider)
    result = use_case.execute(request.amount, request.from_cur, request.to_cur)
    return ConvertResponse.from_result(result)
```

Route handlers are thin. They extract data from the request, call the use case,
and format the response. No business logic, no database queries.

---

## Scenarios

### "I need to add a new feature that sends an email after conversion"

1. Define a `Notifier` Port in `domain/ports.py`
2. Implement `EmailNotifier` in `infrastructure/adapters.py`
3. Create or modify a use case in `application/use_cases.py` that takes a `Notifier`
4. Wire it in `orchestration/main.py`

### "I need to support a new currency"

1. Add it to `SUPPORTED_CURRENCIES` in `domain/constants.py`
2. Add the exchange rates to the infrastructure adapter
3. Add a test in `tests/unit/test_domain.py`
4. Done. No other layer changes.

### "I need to switch from PostgreSQL to MongoDB"

1. Write a new adapter in `infrastructure/adapters.py`
2. Swap the adapter in `orchestration/main.py`
3. Done. Zero changes to domain or application.

### "I need to add a web API on top of my CLI"

1. Add route handlers in `orchestration/routes.py`
2. They call the same use cases as the CLI
3. Done. Domain, infrastructure, and application code are untouched.

### "I need to validate that the amount is not negative"

1. Add `validate_amount()` in `domain/models.py`
2. Call it from the use case in `application/use_cases.py`
3. Add tests in `tests/unit/test_domain.py`
4. Done. Validation works for CLI and web API.

### "I need to log every conversion"

1. Define a `Logger` Port in `domain/ports.py`
2. Implement `StructuredLogger` in `infrastructure/logging.py`
3. Inject it into the use case in `orchestration/main.py`
4. The use case calls `self.logger.info(...)` -- it doesn't know if it's JSON, text, or cloud logging.

---

## Decision tree

```
Is this code about WHAT the business does?
    YES -> domain/
    NO  -> continue

Is this code about HOW to talk to a database, API, or framework?
    YES -> infrastructure/
    NO  -> continue

Is this code about orchestrating domain + infrastructure for a user goal?
    YES -> application/
    NO  -> continue

Is this code about starting the application or handling user input?
    YES -> orchestration/
    NO  -> Re-read the questions. You missed something.
```

---

## Quick reference

| I want to... | Create/modify |
|-------------|--------------|
| Add a business rule | `domain/models.py` |
| Add a validation | `domain/validation.py` |
| Add a new algorithm | `domain/algorithms.py` |
| Add a new external service | `domain/ports.py` + `infrastructure/adapters.py` |
| Add a database table | `infrastructure/persistence/models.py` |
| Add a use case | `application/use_cases.py` |
| Add a CLI command | `orchestration/cli.py` |
| Add a web endpoint | `orchestration/routes.py` |
| Add configuration | `orchestration/config.py` |
| Add a constant | `domain/constants.py` (business) or `infrastructure/config.py` (technical) |
| Add a utility function | `domain/` (if pure) or `infrastructure/` (if framework-dependent) |
| Add a test | `tests/unit/` (domain/application) or `tests/integration/` (orchestration) |
