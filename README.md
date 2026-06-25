# The 4-Layer Architecture

A minimal, universal software architecture template synthesizing
Clean Architecture, Hexagonal Architecture, and Domain-Driven Design
into 4 pragmatic layers with 5 enforceable rules.

## The 4 Layers

```
orchestration/    Who starts what, and when?
application/      What use case is being executed?
domain/           What is true, always? (pure business rules)
infrastructure/   How is it done? (technical adapters)
```

## Where This Comes From

This architecture is not a new invention. It is a synthesis of three
major architectural traditions, reduced to their operational essence.

### 1. Dependency Rule (Robert Martin, Clean Architecture)

Martin's core insight: **dependencies must point inward.**

```
orchestration ──→ application ──→ domain ←── infrastructure
```

- `orchestration` knows about `application`, `infrastructure`, and `domain`
- `application` knows about `domain` (and the Ports it defines)
- `infrastructure` knows about `domain` (it implements the Ports)
- `domain` knows about **nothing** — no frameworks, no databases, no HTTP

The key consequence: you can delete `infrastructure/`, `application/`,
and `orchestration/`, and `domain/` still compiles and passes its tests.
The business logic is fully independent of how it is delivered.

Martin's Clean Architecture has more layers (Entities, Use Cases,
Interface Adapters, Frameworks & Drivers, plus optional Presenters and
Controllers). We collapse them into 4 because in practice, the
distinction between "Interface Adapters" and "Frameworks & Drivers"
creates more ceremony than value for most projects.

### 2. Ports & Adapters (Alistair Cockburn, Hexagonal Architecture)

Cockburn's core insight: **the domain defines interfaces (Ports).
Infrastructure implements them (Adapters).**

```
domain/ports.py           ← The Port (an ABC)
infrastructure/adapters.py ← The Adapter (implements the Port)
```

The domain says "I need exchange rates" by defining `ExchangeRateProvider`
with a method `get_rate(from_cur, to_cur)`. It does not know or care
whether rates come from an HTTP API, a SQL database, or a hardcoded table.

You can swap adapters without touching domain or application code:

```
Port: ExchangeRateProvider
├── ApiExchangeRateProvider      (production)
├── DatabaseExchangeRateProvider (cached)
├── FakeExchangeRateProvider     (unit tests)
└── LoggingExchangeRateProvider  (debugging wrapper)
```

This is the ONLY communication channel between domain and infrastructure.
The domain never calls a framework directly. Infrastructure never contains
business logic.

### 3. Layered Architecture (Eric Evans, Domain-Driven Design)

Evans' core insight: **separate domain logic from application coordination
from technical infrastructure.**

His layers are: User Interface → Application → Domain → Infrastructure.

We keep the same idea but rename them for clarity:
- User Interface → `orchestration/` (broader: CLI, web routes, cron jobs)
- Application → `application/` (use cases, DTOs)
- Domain → `domain/` (entities, value objects, business rules, ports)
- Infrastructure → `infrastructure/` (adapters, framework code)

### Why 4 layers instead of 6-7?

Martin's Clean Architecture has up to 7 conceptual rings:
Entities → Use Cases → Controllers → Gateways → Presenters → Frameworks → Drivers

Evans' DDD has 4 but with a complex internal structure (Aggregates,
Repositories, Domain Services, Application Services, Factories...).

We collapse to 4 because:
- **Fewer decisions.** "Where do I put this file?" has only 4 possible answers.
- **Faster onboarding.** A new developer understands the structure in 5 minutes.
- **Enough separation.** 4 layers provide all the benefits (testability,
  swappability, independence) without the ceremony.
- **Empirically validated.** This exact structure powers CastNet v2 (203 tests,
  23 strategies) and APL Pruning Lab (116 tests, 62 formulas).

### Folder names that say what they do

Martin uses abstract names: "Entities", "Use Cases", "Interface Adapters".
A new developer needs a glossary to understand where to put a file.

We use names that describe the **role**:
- `domain/` — "This is the business. Everything here is true regardless of technology."
- `infrastructure/` — "This is how we connect to the outside world."
- `application/` — "This is what the user asked for."
- `orchestration/` — "This is where we start the engine."

No glossary needed. The folder name IS the explanation.

## The 5 Rules

See [RULES.md](RULES.md) for the full specification with decision trees.

1. **Structure** — 4 folders, no more.
2. **Dependencies** — Arrows point inward. Domain depends on nothing.
3. **Communication** — Ports & Adapters between domain and infrastructure.
4. **Lifecycle** — Only orchestration creates objects. Everything else receives them.
5. **Testing** — Distance from domain = test complexity.

## Documentation

| File | Content |
|------|---------|
| [RULES.md](RULES.md) | The 5 formal rules with decision trees and compliance check |
| [LAYERS.md](LAYERS.md) | Detailed description of each layer with examples and anti-patterns |
| [PORTS_AND_ADAPTERS.md](PORTS_AND_ADAPTERS.md) | Communication patterns between domain and infrastructure |
| [LIFECYCLE.md](LIFECYCLE.md) | Object lifecycle, composition root, dependency injection |
| [TESTING.md](TESTING.md) | Testing strategy per layer, test pyramid, property-based testing |
| [ANTIPATTERNS.md](ANTIPATTERNS.md) | 10 common mistakes and how to fix them |
| [FAQ.md](FAQ.md) | "Where do I put X?" — decision tree and quick reference |

## Quickstart

```bash
git clone git@github.com:graybaud/architecture-4-layers.git
cd architecture-4-layers
python example/orchestration/main.py
# Output: 100.00 EUR = 110.00 USD
python -m pytest example/tests/ -v
```

## Real-world usage

- [CastNet v2](https://github.com/graybaud/castnet) — Sparse LLM inference (203 tests, 23 strategies)
- [APL Pruning Lab](https://github.com/graybaud/apl-pruning-lab) — Mini APL DSL (116 tests, 62 formulas)

## License

MIT — Use it, modify it, ship it.
