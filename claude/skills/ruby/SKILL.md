---
name: ruby
description: Ruby and Rails development patterns for the EasyPost monolith. Covers RSpec testing, mock adapter patterns for microservice interactions, and EasyPost-specific testing conventions.
---

# Ruby / Rails Skill

## EasyPost Monolith: Mock Adapter Pattern

**CRITICAL: Prefer mock adapter pattern over message mocking for microservice interactions.**

The EasyPost monolith uses a **mock adapter pattern** instead of RSpec message mocking (`allow(...).to receive(...)`) for testing interactions with microservices like rUSERS and rUSPS.

### Key Components

1. **Mock Adapter Class**: In-memory implementation matching live service interface (e.g., `SupportUsersMockAdapter`)
2. **RSpec Metadata**: Tests opt-in with `:mock_users` or `:mock_usps` metadata
3. **Factory Integration**: Factories automatically populate mock adapter data
4. **Environment Control**: `MOCK_USERS=1` (default) for fast tests, `MOCK_USERS=0` for integration tests

### Benefits

- Eliminates test pollution from message mocking
- Declarative data setup through factories
- Business logic validation in mock adapter
- Clean tests without scattered `allow(...).to receive(...)` stubs
- Easy switching between mock and live services

### Example

```ruby
# ❌ Before: Message mocking (fragile, pollutes tests)
before do
  allow(UspsRepository).to receive(:carrier_account_mailer_ids)
    .with(carrier_account_id: account.id)
    .and_return([...])
end

# ✅ After: Mock adapter pattern (clean, declarative)
RSpec.describe MyFeature, :mock_users, :mock_usps do
  let(:account) do
    create(:carrier_account, :usps, mailer_ids: [
      { mailer_id: '902513337', sell_at_cost: true }
    ])
  end
end
```

### Documentation

- Full specification: `docs/testing/rusers-test-migration.md`
- Mock implementations: `spec/support/users.rb`, `spec/support/usps.rb`
- Factory examples: `spec/factories/carrier_accounts.rb`

### When Writing Tests

- Use `:mock_users` or `:mock_usps` metadata instead of message mocking
- Configure data through factories, not direct adapter manipulation
- Ensure mock adapter implements same validations as live service
- Test critical paths against live service with `mock_users: false, vcr: :users`

## RSpec Best Practices

### Lint

```bash
arc lint spec/lib/myfile_spec.rb   # Check before submitting diff
```

### File Naming

- Unit tests: `spec/lib/`, `spec/models/`
- Integration tests: `spec/requests/`, `spec/features/`
- Factories: `spec/factories/`
- Support helpers: `spec/support/`
