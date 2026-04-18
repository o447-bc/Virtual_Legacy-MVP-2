---
inclusion: auto
---

# Structured Logging Standards — SoulReel

Every Lambda function and frontend component must follow these logging patterns.

## Backend: Using StructuredLog in a Lambda Function

Import and initialize at the top of every handler:

```python
from structured_logger import StructuredLog

def lambda_handler(event, context):
    log = StructuredLog(event, context)
```

### Logging errors

```python
try:
    # business logic
except ClientError as e:
    log.log_aws_error('DynamoDB', 'GetItem', e, {'TableName': table_name, 'Key': key})
    return error_response(500, 'Server error', e, event, log=log)
except Exception as e:
    log.error('UnexpectedFailure', e)
    return error_response(500, 'Server error', e, event, log=log)
```

### Logging success (INFO level)

Log significant operations at INFO level with duration and context:

```python
import time

start = time.time()
# ... do work ...
elapsed = (time.time() - start) * 1000

log.info('TestScored', details={'testId': test_id, 'domains': len(domains)}, duration_ms=elapsed)
```

### Which operations are "significant" enough for INFO logging

- Video upload started/completed
- Psych test scored
- Data export generated
- Account deletion requested/completed
- Assignment created/accepted/declined
- Billing checkout/subscription change
- Admin settings updated
- Conversation started/completed

### PII handling

The `redact_pii()` function automatically redacts:
- Email addresses → `[REDACTED_EMAIL]`
- Phone numbers (when near phone indicators) → `[REDACTED_PHONE]`
- Known field names (email, phone, name, fullName, firstName, lastName, address, ssn, dateOfBirth) → `[REDACTED]`

Never log raw user content (video transcripts, question responses, conversation text).

## Frontend: Error Reporting

### Using toastError instead of toast.error

```typescript
import { toastError } from '@/utils/toastError';

// Instead of: toast.error(msg)
toastError(msg, 'ComponentName');
```

### Adding X-Correlation-ID to new service files

If you create a new service file with its own `authFetch`:

```typescript
import { getCorrelationId } from '@/services/errorReporter';

async function authFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const idToken = await getIdToken();
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${idToken}`,
      'X-Correlation-ID': getCorrelationId(),
      ...options.headers,
    },
  });
  // ...
}
```

### Wiring up error reporting in new React components

In ErrorBoundary-style components:

```typescript
import { reportError } from '@/services/errorReporter';

reportError({
  errorMessage: error.message,
  component: 'MyComponent',
  url: window.location.href,
  stackTrace: error.stack,
  errorType: error.name,
  metadata: {
    userAgent: navigator.userAgent,
    route: window.location.pathname,
  },
});
```

## Adding metric filters for newly migrated Lambdas

When migrating a Lambda to use StructuredLog, add a metric filter in template.yml:

```yaml
MyFunctionErrorMetricFilter:
  Type: AWS::Logs::MetricFilter
  Properties:
    LogGroupName: !Sub /aws/lambda/${MyFunction}
    FilterPattern: '{ $.level = "ERROR" && $.source = "backend" }'
    MetricTransformations:
      - MetricNamespace: SoulReel/Errors
        MetricName: MyFunctionErrorCount
        MetricValue: '1'
        DefaultValue: 0
```
