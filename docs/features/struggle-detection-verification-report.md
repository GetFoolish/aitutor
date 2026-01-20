# Verification Report

**Generated:** 2026-01-16 13:17:16
**Status:** FAILED
**Duration:** 2.3s

## Summary

| Metric | Value |
|--------|-------|
| Total Evidence | 13 |
| Passed | 12 |
| Failed | 1 |
| Criteria Total | 5 |
| Criteria Verified | 0 |
| Pass Rate | 0% |

## Acceptance Criteria

- ❌ **SC-1**: System detects struggle signals: long pauses, repeated errors, inactivity
- ❌ **SC-2**: Automatic intervention with appropriate support level
- ❌ **SC-3**: Intervention types: hints, encouragement, problem simplification, break suggestion
- ❌ **SC-4**: Interventions feel natural and supportive, not robotic
- ❌ **SC-5**: Tracking of intervention effectiveness for continuous improvement

## Evidence Details

### 1. Command Output - ✅ PASSED

**Input:** ``
**Timestamp:** 2026-01-16T13:17:14.313442
**Status Code:** 0

**Output:**
```

```

### 2. Command Output - ✅ PASSED

**Input:** ``
**Timestamp:** 2026-01-16T13:17:14.321649
**Status Code:** 0

**Output:**
```

```

### 3. Command Output - ✅ PASSED

**Input:** ``
**Timestamp:** 2026-01-16T13:17:14.373956
**Status Code:** 0

**Output:**
```

```

### 4. Command Output - ✅ PASSED

**Input:** ``
**Timestamp:** 2026-01-16T13:17:14.386142
**Status Code:** 0

**Output:**
```

```

### 5. Api Response - ❌ FAILED

**Input:** `POST http://localhost:8001/session/{session_id}/record_activity`
**Timestamp:** 2026-01-16T13:17:16.425858
**Status Code:** 405
**Response Time:** 10ms
**Error:** Expected status 200, got 405

**Output:**
```
{"detail":"Method Not Allowed"}
```

### 6. Command Output - ✅ PASSED

**Input:** ``
**Timestamp:** 2026-01-16T13:17:16.495546
**Status Code:** 0

**Output:**
```

```

### 7. Command Output - ✅ PASSED

**Input:** ``
**Timestamp:** 2026-01-16T13:17:16.509617
**Status Code:** 0

**Output:**
```

```

### 8. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T13:17:16.525425
**Status Code:** 200
**Response Time:** 15ms

**Output:**
```
Status: 200, Content-Length: 2188
```

### 9. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T13:17:16.535075
**Status Code:** 200
**Response Time:** 10ms

**Output:**
```
Status: 200, Content-Length: 2188
```

### 10. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T13:17:16.545590
**Status Code:** 200
**Response Time:** 10ms

**Output:**
```
Status: 200, Content-Length: 2188
```

### 11. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T13:17:16.555182
**Status Code:** 200
**Response Time:** 10ms

**Output:**
```
Status: 200, Content-Length: 2188
```

### 12. Command Output - ✅ PASSED

**Input:** `manual verification: Test intervention effectiveness tracking`
**Timestamp:** 2026-01-16T13:17:16.555226
**Status Code:** 0

**Output:**
```
Manual verification required - skipped in automated run
```

### 13. Command Output - ✅ PASSED

**Input:** `manual verification: Verify interventions don't spam or feel robotic`
**Timestamp:** 2026-01-16T13:17:16.555235
**Status Code:** 0

**Output:**
```
Manual verification required - skipped in automated run
```
