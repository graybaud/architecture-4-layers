# Anti-Patterns -- Common Mistakes and How to Fix Them

## 1. Domain imports infrastructure

**The mistake:**

```python
# domain/models.py
from infrastructure.database import get_connection  # NO

def get_rate(from_cur, to_cur):
    conn = get_connection()
    return conn.execute("SELECT rate FROM rates WHERE ...")
```

**Why it's wrong:**
- Domain is now coupled to a specific database
- Cannot test without a database
- Cannot swap databases without changing domain code

**The fix:**

```python
# domain/ports.py
class ExchangeRateProvider(ABC):
    @abstractmethod
    def get_rate(self, from_cur: str, to_cur: str) -> float: ...

# domain/models.py
def convert(amount: float, rate: float) -> float:
    return amount * rate

# infrastructure/adapters.py
class PostgresExchangeRateProvider(ExchangeRateProvider):
    def get_rate(self, from_cur, to_cur):
        conn = get_connection()
        return conn.execute(...)
```

---

## 2. Use case creates its own dependencies

**The mistake:**

```python
# application/use_cases.py
class ConvertCurrencyUseCase:
    def execute(self, amount, from_cur, to_cur):
        provider = ApiExchangeRateProvider(api_key="secret")  # NO
        rate = provider.get_rate(from_cur, to_cur)
        return convert(amount, rate)
```

**Why it's wrong:**
- Cannot test with a fake provider
- API key is hardcoded in business logic
- Violates the lifecycle rule

**The fix:**

```python
class ConvertCurrencyUseCase:
    def __init__(self, rate_provider: ExchangeRateProvider):  # Injected
        self.rate_provider = rate_provider

    def execute(self, amount, from_cur, to_cur):
        rate = self.rate_provider.get_rate(from_cur, to_cur)
        return convert(amount, rate)
```

---

## 3. Orchestration contains business logic

**The mistake:**

```python
# orchestration/main.py
def main():
    amount = float(input("Amount: "))
    if amount < 0:  # NO -- business rule in orchestration
        print("Amount must be positive")
        return
    if amount > 10000:  # NO -- another business rule
        print("Amount too large")
        return
    # ... more business rules ...
    result = use_case.execute(amount, "EUR", "USD")
```

**Why it's wrong:**
- Business rules are scattered across layers
- Rules cannot be reused (e.g., in a web endpoint)
- Testing requires running the full CLI

**The fix:**

```python
# domain/models.py
def validate_amount(amount: float) -> None:
    if amount < 0:
        raise ValueError("Amount must be non-negative")
    if amount > 10000:
        raise ValueError("Amount exceeds maximum")

# application/use_cases.py
class ConvertCurrencyUseCase:
    def execute(self, amount, from_cur, to_cur):
        validate_amount(amount)  # Domain rule, reusable
        rate = self.rate_provider.get_rate(from_cur, to_cur)
        return ConvertResult(...)

# orchestration/main.py
def main():
    try:
        result = use_case.execute(100, "EUR", "USD")
    except ValueError as e:
        print(e)
        return
```

---

## 4. Infrastructure contains business logic

**The mistake:**

```python
# infrastructure/adapters.py
class ApiExchangeRateProvider(ExchangeRateProvider):
    def get_rate(self, from_cur, to_cur):
        rate = self._fetch_from_api()
        if rate > 2.0:  # NO -- business rule in infrastructure
            raise ValueError("Rate too high, possible error")
        return rate
```

**Why it's wrong:**
- Business rules are hidden in technical code
- Rules cannot be tested independently
- Swapping the adapter loses the rule

**The fix:**

```python
# infrastructure/adapters.py
class ApiExchangeRateProvider(ExchangeRateProvider):
    def get_rate(self, from_cur, to_cur):
        return self._fetch_from_api()  # Just return data

# domain/models.py
def validate_rate(rate: float) -> None:
    if rate > 2.0:
        raise ValueError("Rate exceeds sanity threshold")

# application/use_cases.py
class ConvertCurrencyUseCase:
    def execute(self, amount, from_cur, to_cur):
        rate = self.rate_provider.get_rate(from_cur, to_cur)
        validate_rate(rate)  # Domain rule applied here
        ...
```

---

## 5. Adapter without a Port

**The mistake:**

```python
# infrastructure/adapters.py
class ApiExchangeRateProvider:  # No parent class
    def get_rate(self, from_cur, to_cur):
        ...
```

**Why it's wrong:**
- No contract -- nothing guarantees the method signature
- Use case must import the concrete class (breaks dependency rule)
- Cannot swap implementations without changing use case code

**The fix:**

```python
# domain/ports.py
class ExchangeRateProvider(ABC):
    @abstractmethod
    def get_rate(self, from_cur: str, to_cur: str) -> float: ...

# infrastructure/adapters.py
class ApiExchangeRateProvider(ExchangeRateProvider):  # Implements Port
    def get_rate(self, from_cur, to_cur):
        ...
```

---

## 6. Port in infrastructure

**The mistake:**

```
infrastructure/
    ports.py  # NO -- Ports belong in domain
    adapters.py
```

**Why it's wrong:**
- Domain must import infrastructure to use the Port
- Violates the dependency rule
- Cannot reuse domain without infrastructure

**The fix:**

```
domain/
    ports.py  # Ports live here
    models.py
infrastructure/
    adapters.py  # Only implementations
```

---

## 7. God Port

**The mistake:**

```python
# domain/ports.py
class DataProvider(ABC):
    def get_rate(self, ...): ...
    def save_order(self, ...): ...
    def send_email(self, ...): ...
    def upload_file(self, ...): ...
    def log_event(self, ...): ...
```

**Why it's wrong:**
- Violates Interface Segregation Principle
- Use cases depend on methods they don't need
- Hard to mock (must implement everything)

**The fix:**

```python
class ExchangeRateProvider(ABC):
    def get_rate(self, ...): ...

class OrderRepository(ABC):
    def save(self, order): ...
    def find_by_id(self, order_id): ...

class Notifier(ABC):
    def send(self, message): ...

class FileStorage(ABC):
    def upload(self, path, data): ...
```

---

## 8. Skipping the application layer

**The mistake:**

```python
# orchestration/main.py
def main():
    provider = ApiExchangeRateProvider()
    rate = provider.get_rate("EUR", "USD")
    result = convert(100, rate)  # Domain called directly
    print(f"100 EUR = {result} USD")
```

**Why it's wrong:**
- No use case -- coordination logic lives in orchestration
- Cannot reuse this logic (web endpoint needs a copy-paste)
- Validation and error handling scattered

**The fix:**

```python
# application/use_cases.py
class ConvertCurrencyUseCase:
    def __init__(self, rate_provider):
        self.rate_provider = rate_provider

    def execute(self, amount, from_cur, to_cur):
        rate = self.rate_provider.get_rate(from_cur, to_cur)
        converted = convert(amount, rate)
        return ConvertResult(amount, converted, from_cur, to_cur)

# orchestration/main.py
def main():
    provider = ApiExchangeRateProvider()
    use_case = ConvertCurrencyUseCase(provider)
    result = use_case.execute(100, "EUR", "USD")
    print(result)
```

---

## 9. Circular dependencies between layers

**The mistake:**

```python
# domain/models.py
from application.use_cases import ConvertCurrencyUseCase  # NO

# application/use_cases.py
from domain.models import convert  # OK, but the reverse is not
```

**Why it's wrong:**
- Creates import cycles
- Domain should never know about application

**The fix:**
- Domain never imports from application, infrastructure, or orchestration
- If domain needs to trigger behavior, use events or callbacks (advanced)

---

## 10. Business logic in DTOs

**The mistake:**

```python
# application/dtos.py
@dataclass
class ConvertResult:
    amount: float
    converted: float
    from_currency: str
    to_currency: str

    def format(self) -> str:  # NO -- business logic in DTO
        if self.converted > 1000:
            return f"Large: {self.converted}"
        return str(self.converted)
```

**Why it's wrong:**
- DTOs should be pure data, no behavior
- Formatting logic should be in domain or a separate presenter

**The fix:**

```python
# domain/models.py
def format_result(result: ConvertResult) -> str:
    if result.converted > 1000:
        return f"Large: {result.converted}"
    return str(result.converted)
```

---

## Quick self-check

Ask yourself these questions about your codebase:

| Question | If yes, you have a problem |
|----------|---------------------------|
| Does any file in `domain/` import from `infrastructure/`? | Anti-pattern 1 |
| Does any use case create its own dependencies with `new`? | Anti-pattern 2 |
| Does `orchestration/` contain `if` statements about business rules? | Anti-pattern 3 |
| Do any infrastructure classes raise domain exceptions based on data values? | Anti-pattern 4 |
| Are there public classes in `infrastructure/` that don't inherit from a domain ABC? | Anti-pattern 5 |
| Is there a `ports.py` in `infrastructure/`? | Anti-pattern 6 |
| Does any Port have more than 5 methods? | Anti-pattern 7 |
| Does orchestration call domain functions directly? | Anti-pattern 8 |
