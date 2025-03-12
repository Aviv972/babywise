# Redis Migration Guide: aioredis to redis.asyncio

This document outlines the migration strategy from `aioredis` to `redis.asyncio` (redis-py v4.2+) for the Babywise Chatbot project.

## Background

Python 3.12 removed the `distutils` module, which `aioredis` depends on. Since `aioredis` is also deprecated in favor of the asyncio support built into redis-py, this migration provides a long-term solution rather than continuously applying patches.

## Migration Strategy

Our migration follows a phased approach to minimize risks to core application functionality, especially the workflow components:

### Phase 1: Compatibility Layer

We've created a compatibility layer (`backend/services/redis_compat.py`) that:

- Provides the same API regardless of the underlying Redis client
- Supports both `aioredis` and `redis.asyncio` via a feature flag
- Includes robust error handling and memory fallback

### Phase 2: Service Adaptation

The `backend/services/redis_service.py` has been modified to:

- Import from the compatibility layer instead of directly from `aioredis`
- Maintain the exact same API for all consuming components
- Simplify the code by removing redundant implementations

### Phase 3: Testing

A comprehensive test script (`test_redis_migration.py`) verifies:

- Basic connection functionality
- Thread state persistence
- Routine cache operations
- List operations
- Multiple operations
- Memory fallback mechanisms

### Phase 4: Dependency Management

Both `aioredis` and `redis-py` are included as dependencies during the migration:

```
aioredis==2.0.0
redis>=4.2.0
```

## Implementation Details

### Compatibility Layer

The compatibility layer uses a feature flag to switch between backends:

```python
# Determine which Redis client to use
USE_REDIS_ASYNCIO = True  # Set to True to use redis.asyncio, False for aioredis
```

It implements connection management that works with both backends:

```python
@contextlib.asynccontextmanager
async def redis_connection():
    # ...
    if USE_REDIS_ASYNCIO:
        # Modern redis.asyncio approach
        client = await redis.Redis.from_url(...)
    else:
        # Legacy aioredis approach
        client = await redis.from_url(...)
    # ...
```

### API Consistency

All functions maintain the same signature and behavior:

```python
async def get_thread_state(thread_id: str) -> Optional[Dict[str, Any]]:
    # Same function signature and behavior
    # Only the underlying implementation changes
```

## Testing the Migration

To test the migration:

1. Set `USE_REDIS_ASYNCIO = True` in `backend/services/redis_compat.py`
2. Run the test script:
   ```bash
   python test_redis_migration.py
   ```
3. Monitor your application logs for any Redis-related errors

## Rollback Plan

If issues arise:

1. Set `USE_REDIS_ASYNCIO = False` in `backend/services/redis_compat.py`
2. Redeploy the application
3. Verify with the test script

No other code changes are needed for rollback since all components use the same API.

## Verifying Workflow Functionality

The migration specifically preserves the API used by workflow components:

- Thread state persistence in workflow.py is unaffected
- Routine tracking in command_processor.py continues to work identically
- All Redis operations maintain the same behavior

## Next Steps

After confirming the migration works in production:

1. Remove the compatibility layer
2. Update all imports to directly use `redis.asyncio`
3. Remove `aioredis` from dependencies

## References

- [Redis-py Documentation](https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html)
- [Python 3.12 Removal of distutils](https://docs.python.org/3.12/whatsnew/3.12.html#removed) 