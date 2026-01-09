# Contributing to Lattice

## Development Setup

1. Clone the repository
2. Install Rust via rustup (<https://rustup.rs>)
3. Install Python 3.11 or later
4. Install maturin: `pip install maturin`
5. Build the project: `cd lattice-core && maturin develop`

## Code Standards

### Rust Code

- Follow the Rust API Guidelines (<https://rust-lang.github.io/api-guidelines/>)
- Use `cargo fmt` before committing
- Use `cargo clippy` to check for common issues
- All public APIs must have documentation comments
- Avoid `unwrap()` in library code; use proper error handling

### Python Code

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Use `ruff` for linting
- All public functions must have docstrings

### Documentation

- Write clear, technical documentation without marketing language
- Explain the "why" not just the "what"
- Include code examples where appropriate
- Keep documentation in sync with code changes

## Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types: feat, fix, docs, refactor, test, chore

Example:

```
feat(core): implement signal dependency tracking

Add automatic dependency tracking when signals are accessed
within a reactive context. Uses a thread-local stack to
track the currently executing computation.
```

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass
4. Update documentation as needed
5. Submit PR with clear description of changes

## Testing

```bash
# Rust tests
cd lattice-core
cargo test

# Python tests
pytest tests/

# Integration tests
pytest tests/integration/
```

## Architecture Decisions

Major architectural decisions should be documented in `docs/adr/` using the
Architecture Decision Record format. See existing ADRs for examples.
