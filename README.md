# Architecture 4 Layers + Hexagonal

Minimal, universal software architecture template.
4 layers, 5 rules, 0 dependencies between domain and infrastructure.

## The 4 Layers

```
orchestration/    Who starts what, and when?
application/      What use case is being executed?
domain/           What is true, always? (pure business rules)
infrastructure/   How is it done? (technical adapters)
```

## The 5 Rules

1. **Structure** -- 4 folders, no more.
2. **Dependencies** -- Arrows point inward. Domain depends on nothing.
3. **Communication** -- Ports & Adapters between domain and infrastructure.
4. **Lifecycle** -- Only orchestration creates objects. Everything else receives them.
5. **Testing** -- Distance from domain = test complexity.

See [RULES.md](RULES.md) for the full specification.

## Quickstart

```bash
git clone git@github.com:graybaud/architecture-4-layers.git
cd architecture-4-layers

# Run the example
python example/orchestration/main.py
# Output: 100.00 EUR = 110.00 USD

# Run the tests
python -m pytest example/tests/ -v
```

## Documentation

| File | Content |
|------|---------|
| [RULES.md](RULES.md) | The 5 formal rules with decision trees and compliance check |
| [LAYERS.md](LAYERS.md) | Detailed description of each layer with examples and anti-patterns |
| [PORTS_AND_ADAPTERS.md](PORTS_AND_ADAPTERS.md) | Communication patterns between domain and infrastructure |
| [LIFECYCLE.md](LIFECYCLE.md) | Object lifecycle, composition root, dependency injection |
| [TESTING.md](TESTING.md) | Testing strategy per layer, test pyramid, property-based testing |
| [ANTIPATTERNS.md](ANTIPATTERNS.md) | 10 common mistakes and how to fix them |
| [FAQ.md](FAQ.md) | "Where do I put X?" -- decision tree and quick reference |

## Example

```
example/
    domain/
        models.py         # Pure business logic
        ports.py           # Interfaces (ABCs)
    infrastructure/
        adapters.py        # Port implementations
    application/
        use_cases.py       # Use cases
    orchestration/
        main.py            # Entry point (composition root)
    tests/
        test_all.py        # 12 tests, 3 layers, 0 mocks for domain
```

## Origin

Synthesis of:
- **Clean Architecture** (Robert Martin) -- dependency rule, use cases, entities
- **Hexagonal Architecture** (Alistair Cockburn) -- Ports & Adapters
- **Domain-Driven Design** (Eric Evans) -- layered architecture, repositories

## Real-world usage

This architecture powers:
- [CastNet v2](https://github.com/graybaud/castnet) -- Sparse LLM inference (203 tests, 23 strategies)
- [APL Pruning Lab](https://github.com/graybaud/apl-pruning-lab) -- Mini APL DSL (109 tests, 55 formulas)

## License

MIT -- Use it, modify it, ship it.
