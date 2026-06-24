# Testing Strategy -- Per Layer

## The golden rule

> The further a layer is from the domain, the slower and more complex its tests.

This is not a design choice. It is a consequence of the dependency rule.
Domain code has no dependencies, so its tests are instant. Orchestration
code depends on everything, so its tests need real infrastructure.

## Test types by layer

### Domain -- Pure unit tests

**Characteristics:**
- No mocks needed
- No filesystem, network, or GPU
- Tests run in milliseconds
- Should be 60-70% of your total tests

**What to test:**
- Every business rule
- Every algorithm
- Every value object method
- Edge cases: zero, negative, empty, very large, NaN
- Exceptions and error conditions

**Example:**

```python
# tests/unit/test_domain.py

def test_convert_simple():
    assert convert(100, 1.10) == 110.0

def test_convert_zero():
    assert convert(0, 1.10) == 0.0

def test_convert_negative_raises():
    with pytest.raises(ValueError, match="non-negative"):
        convert(-100, 1.10)

def test_convert_rounding():
    assert convert(100, 1.105) == 110.50  # Rounds to 2 decimals

def test_convert_large_amount():
    assert convert(1_000_000, 1.10) == 1_100_000.0
```

**Anti-pattern:**

```python
# WRONG -- domain test needs a database
def test_convert():
    db = Database("postgres://...")  # NO
    rate = db.get_rate("EUR", "USD")
    assert convert(100, rate) == 110.0
```

### Infrastructure -- Unit tests with real resources or mocks

**Characteristics:**
- May use `tmp_path` for file I/O
- May use real libraries (safetensors, sqlite in-memory)
- May use mocks for external services (APIs, GPUs)
- Tests run in milliseconds to seconds
- Should be 10-20% of your total tests

**What to test:**
- That the adapter correctly implements the Port
- Serialization/deserialization (save then load)
- Error translation (Http404 -> CurrencyNotFoundError)
- Edge cases: empty files, missing keys, malformed data

**Example with real file I/O:**

```python
# tests/unit/test_infrastructure.py

def test_save_and_load_scores(tmp_path):
    persister = SafetensorsScorePersister()
    scores = {"layer0": torch.randn(5, 10)}
    path = str(tmp_path / "scores.safetensors")

    persister.save(scores, path)
    loaded = persister.load(path)

    assert torch.equal(loaded["layer0"], scores["layer0"])


def test_load_nonexistent_file_raises(tmp_path):
    persister = SafetensorsScorePersister()
    path = str(tmp_path / "nonexistent.safetensors")

    with pytest.raises(FileNotFoundError):
        persister.load(path)
```

**Example with mock:**

```python
def test_api_provider_raises_on_404():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 404
        provider = ApiExchangeRateProvider("fake-key")

        with pytest.raises(CurrencyNotFoundError):
            provider.get_rate("EUR", "USD")
```

### Application -- Unit tests with fake adapters

**Characteristics:**
- Uses fake implementations of Ports
- No mocks (fakes are real objects, just simplified)
- Tests run in milliseconds
- Should be 20-25% of your total tests

**What to test:**
- The use case orchestrates correctly
- The DTO is returned with correct values
- Error propagation from domain/infrastructure
- Edge cases: empty results, missing data

**Example:**

```python
# tests/unit/test_application.py

class FakeExchangeRateProvider(ExchangeRateProvider):
    def get_rate(self, from_cur, to_cur):
        if (from_cur, to_cur) == ("EUR", "USD"):
            return 1.10
        raise CurrencyNotFoundError(f"No rate for {from_cur} -> {to_cur}")


def test_convert_eur_to_usd():
    provider = FakeExchangeRateProvider()
    use_case = ConvertCurrencyUseCase(provider)

    result = use_case.execute(100, "EUR", "USD")

    assert result.amount == 100
    assert result.converted == 110.0
    assert result.from_currency == "EUR"
    assert result.to_currency == "USD"


def test_unknown_currency_propagates_error():
    provider = FakeExchangeRateProvider()
    use_case = ConvertCurrencyUseCase(provider)

    with pytest.raises(CurrencyNotFoundError):
        use_case.execute(100, "EUR", "JPY")
```

### Orchestration -- Integration tests

**Characteristics:**
- Uses real adapters (or very close to real)
- May need a real database, real files, or a tiny model
- Tests run in seconds
- Should be < 5% of your total tests

**What to test:**
- The composition root wires everything correctly
- The end-to-end happy path works
- Configuration is loaded correctly

**Example:**

```python
# tests/integration/test_cli.py

def test_extract_scores_end_to_end(tmp_path):
    # Real model (tiny one for CI), real dataset, real persister
    model = HuggingFaceWeightProvider("sshleifer/tiny-gpt2", "cpu")
    dataset = WikiTextProvider("sshleifer/tiny-gpt2", max_len=32)
    collector = ActivationCollector(model.model, ffn_names)
    persister = SafetensorsScorePersister()
    strategy = WandaStrategy()

    use_case = ExtractScoresUseCase(strategy, model, dataset, collector, persister)
    output_path = str(tmp_path / "scores.safetensors")

    result = use_case.execute(num_batches=2, output_path=output_path)

    assert result.num_layers > 0
    assert os.path.exists(output_path)
```

## Test distribution pyramid

```
          /\
         /  \       Orchestration  < 5%   (slow, real infra)
        /    \
       /------\     Application    ~20%   (fast, fake adapters)
      /        \
     /----------\   Infrastructure ~15%   (fast, real files or mocks)
    /            \
   /--------------\ Domain          ~60%   (instant, no deps)
  /________________\
```

## What NOT to test

- **Framework internals.** Don't test that `torch.load` works. It does.
- **Third-party APIs.** Don't test that `requests.get` returns data. Mock it.
- **Generated code.** Don't test getters, setters, or `__repr__` methods.
- **Configuration values.** Don't test that `config.yaml` has the right keys.
  Test that your code handles missing or invalid config.

## Property-based testing

For domain algorithms, consider testing mathematical invariants:

```python
# tests/unit/test_properties.py

def test_magnitude_scale_invariant():
    """Magnitude(W) and Magnitude(k*W) should be identical after normalization."""
    W = torch.randn(5, 10)
    k = 3.0

    strategy = MagnitudeStrategy()
    s1 = strategy.calculate(fake_weights(W), fake_activations(None), "test")
    s2 = strategy.calculate(fake_weights(W * k), fake_activations(None), "test")

    assert torch.allclose(s1, s2, atol=1e-6)


def test_mask_monotonicity():
    """Larger keep_fraction should keep more connections."""
    scores = torch.rand(10, 10)
    n_03 = apply_percentile_mask(scores, 0.3).sum()
    n_05 = apply_percentile_mask(scores, 0.5).sum()
    n_08 = apply_percentile_mask(scores, 0.8).sum()

    assert n_03 <= n_05 <= n_08
```

## Running tests

```bash
# All tests
pytest tests/ -v

# Only unit tests (fast, no GPU)
pytest tests/unit/ -v

# Only integration tests (needs real model)
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=. --cov-report=term-missing
```

## Summary

| Layer | Test type | Dependencies | Speed | % of tests |
|-------|-----------|-------------|-------|------------|
| `domain/` | Pure unit | None | < 1s | 60-70% |
| `infrastructure/` | Unit + mocks | `tmp_path`, mocks | < 1s | 10-20% |
| `application/` | Unit + fakes | Fake adapters | < 1s | 20-25% |
| `orchestration/` | Integration | Real adapters | > 1s | < 5% |
