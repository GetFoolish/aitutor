# Verification Report

**Generated:** 2026-01-16 17:50:28
**Status:** FAILED
**Duration:** 9.7s

## Summary

| Metric | Value |
|--------|-------|
| Total Evidence | 16 |
| Passed | 13 |
| Failed | 3 |

## Services

**Started:** uvicorn-3000

## Evidence Details

### 1. Api Response - ✅ PASSED

**Input:** `GET http://localhost:8004/health`
**Timestamp:** 2026-01-16T17:50:21.501038
**Status Code:** 200
**Response Time:** 27ms

**Output:**
```
{"status":"healthy","service":"HomeworkAssistant"}
```

### 2. Api Response - ❌ FAILED

**Input:** `POST http://localhost:8004/homework/upload`
**Timestamp:** 2026-01-16T17:50:23.584205
**Status Code:** 422
**Response Time:** 25ms
**Error:** Expected status 200, got 422

**Output:**
```
{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}
```

### 3. Api Response - ❌ FAILED

**Input:** `POST http://localhost:8004/homework/assist`
**Timestamp:** 2026-01-16T17:50:25.704557
**Status Code:** 401
**Response Time:** 74ms
**Error:** Expected status 200, got 401

**Output:**
```
{"detail":"Missing or invalid authorization header"}
```

### 4. Api Response - ❌ FAILED

**Input:** `GET http://localhost:8004/homework/list`
**Timestamp:** 2026-01-16T17:50:27.778373
**Status Code:** 401
**Response Time:** 18ms
**Error:** Expected status 200, got 401

**Output:**
```
{"detail":"Missing or invalid authorization header"}
```

### 5. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T17:50:27.796532
**Status Code:** 200
**Response Time:** 18ms

**Output:**
```
Status: 200, Content-Length: 2204
```

### 6. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T17:50:27.808243
**Status Code:** 200
**Response Time:** 12ms

**Output:**
```
Status: 200, Content-Length: 2204
```

### 7. Command Output - ✅ PASSED

**Input:** ``
**Timestamp:** 2026-01-16T17:50:27.831305
**Status Code:** 0

**Output:**
```

```

### 8. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T17:50:27.852024
**Status Code:** 200
**Response Time:** 20ms

**Output:**
```
Status: 200, Content-Length: 2204
```

### 9. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T17:50:27.870642
**Status Code:** 200
**Response Time:** 18ms

**Output:**
```
Status: 200, Content-Length: 2204
```

### 10. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T17:50:27.885705
**Status Code:** 200
**Response Time:** 15ms

**Output:**
```
Status: 200, Content-Length: 2204
```

### 11. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T17:50:27.904162
**Status Code:** 200
**Response Time:** 18ms

**Output:**
```
Status: 200, Content-Length: 2204
```

### 12. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T17:50:27.920967
**Status Code:** 200
**Response Time:** 17ms

**Output:**
```
Status: 200, Content-Length: 2204
```

### 13. Command Output - ✅ PASSED

**Input:** `manual verification: Add error handling for file uploads and API failures`
**Timestamp:** 2026-01-16T17:50:27.921003
**Status Code:** 0

**Output:**
```
Manual verification required - skipped in automated run
```

### 14. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T17:50:27.936799
**Status Code:** 200
**Response Time:** 16ms

**Output:**
```
Status: 200, Content-Length: 2204
```

### 15. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T17:50:27.953069
**Status Code:** 200
**Response Time:** 16ms

**Output:**
```
Status: 200, Content-Length: 2204
```

### 16. E2E Http Fallback - ✅ PASSED

**Input:** `E2E (HTTP fallback): browser verification @ http://localhost:3000`
**Timestamp:** 2026-01-16T17:50:27.980697
**Status Code:** 200
**Response Time:** 27ms

**Output:**
```
Status: 200, Content-Length: 2204
```
