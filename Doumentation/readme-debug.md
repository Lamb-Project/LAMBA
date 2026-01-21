# LAMBA Debug Guide

This document describes debugging tools and procedures for troubleshooting LAMBA, particularly for AI evaluation issues.

## Table of Contents

- [LAMB API Debugging](#lamb-api-debugging)
- [Common Issues](#common-issues)
- [Debug Endpoints](#debug-endpoints)
- [Log Analysis](#log-analysis)

---

## LAMB API Debugging

The LAMB API is used for automatic AI evaluation of student submissions. When evaluation fails, the following tools can help diagnose the issue.

### Configuration Check

Ensure the following environment variables are correctly set in your `.env` file:

```env
# LAMB API Configuration
LAMB_API_URL=http://lamb.lamb-project.org:9099
LAMB_BEARER_TOKEN=your_token_here
LAMB_TIMEOUT=30
```

### Debug Endpoints

LAMBA provides admin debug endpoints to test the LAMB API connection:

#### 1. Test LAMB Connection

**Endpoint:** `GET /api/admin/debug/lamb`

**Requires:** Admin session

**Response:**
```json
{
  "success": true,
  "debug_info": {
    "config": {
      "LAMB_API_URL": "http://lamb.lamb-project.org:9099",
      "LAMB_BEARER_TOKEN": "0p3n-w3bu!...",
      "LAMB_TIMEOUT": 30
    },
    "tests": {
      "connectivity": {
        "url": "http://lamb.lamb-project.org:9099/v1/models",
        "status_code": 200,
        "response_length": 1234,
        "content_type": "application/json",
        "json_parsed": true,
        "models_count": 5,
        "available_models": ["lamb_assistant.model1", "lamb_assistant.model2", ...]
      }
    }
  }
}
```

**Usage (curl):**
```bash
curl -X GET "https://your-lamba-server/api/admin/debug/lamb" \
     -H "Cookie: admin_session=YOUR_SESSION_TOKEN"
```

#### 2. Verify Specific Model

**Endpoint:** `POST /api/admin/debug/lamb/verify-model`

**Requires:** Admin session

**Body:**
```json
{
  "evaluator_id": "your-evaluator-id"
}
```

**Response:**
```json
{
  "success": true,
  "evaluator_id": "your-evaluator-id",
  "model_id": "lamb_assistant.your-evaluator-id",
  "verification_result": {
    "success": true,
    "model_id": "lamb_assistant.your-evaluator-id",
    "message": "Modelo lamb_assistant.your-evaluator-id encontrado correctamente"
  }
}
```

**Usage (curl):**
```bash
curl -X POST "https://your-lamba-server/api/admin/debug/lamb/verify-model" \
     -H "Content-Type: application/json" \
     -H "Cookie: admin_session=YOUR_SESSION_TOKEN" \
     -d '{"evaluator_id": "your-evaluator-id"}'
```

---

## Common Issues

### 1. "Expecting value: line 1 column 1 (char 0)"

**Cause:** The LAMB API returned an empty response or non-JSON content.

**Possible reasons:**
- Wrong `LAMB_API_URL` configuration
- LAMB server is not running
- Network connectivity issue between LAMBA and LAMB servers
- Firewall blocking the connection
- Authentication issue

**Debug steps:**
1. Check the LAMB API URL in your `.env` file
2. Test connectivity using the debug endpoint: `GET /api/admin/debug/lamb`
3. Check if the LAMB server is accessible from the LAMBA container:
   ```bash
   docker exec -it lamba-backend curl http://lamb.lamb-project.org:9099/v1/models
   ```

### 2. "No se encontró el modelo 'lamb_assistant.XXX' en el servidor LAMB"

**Cause:** The evaluator ID configured in the activity doesn't exist on the LAMB server.

**Debug steps:**
1. Use the debug endpoint to list available models
2. Verify the evaluator ID in the activity configuration matches an existing model
3. The model ID format is: `lamb_assistant.{evaluator_id}`

### 3. "Esta actividad no tiene configurado un ID de evaluador"

**Cause:** The activity doesn't have an `evaluator_id` set.

**Solution:**
1. Edit the activity
2. Set the "Evaluator ID" field to a valid LAMB model ID

### 4. Timeout errors

**Cause:** The LAMB API is taking too long to respond.

**Solutions:**
- Increase `LAMB_TIMEOUT` in your `.env` file
- Check LAMB server performance
- Reduce the size of documents being evaluated

---

## Log Analysis

### Enable Debug Logging

To see more detailed logs, you can adjust the logging level:

```python
# In config.py or main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Key Log Messages

When evaluating submissions, look for these log messages:

```
INFO:root:Verificando modelo LAMB en: http://...
INFO:root:LAMB /v1/models response status: 200
INFO:root:Buscando modelo 'lamb_assistant.XXX' entre N modelos disponibles
INFO:root:Enviando solicitud de evaluación al modelo LAMB lamb_assistant.XXX
INFO:root:URL: http://.../chat/completions, Timeout: 30s, Text length: 1234 chars
INFO:root:LAMB /chat/completions response status: 200
INFO:root:Respuesta de evaluación recibida de LAMB
```

### Docker Logs

To view real-time logs from the backend container:

```bash
docker compose logs -f backend
```

To filter for LAMB-related messages:

```bash
docker compose logs backend 2>&1 | grep -i lamb
```

---

## Evaluation Flow

Understanding the evaluation flow helps with debugging:

```
1. Teacher clicks "Evaluate" button
   ↓
2. POST /api/activities/{id}/evaluate
   ↓
3. GradeService.create_automatic_evaluation_for_activity()
   ↓
4. LAMBAPIService.verify_model_exists(evaluator_id)
   → GET {LAMB_API_URL}/v1/models
   → Check if lamb_assistant.{evaluator_id} exists
   ↓
5. For each submission without grade:
   a. DocumentExtractor.extract_text_from_file()
   b. LAMBAPIService.evaluate_text(text, evaluator_id)
      → POST {LAMB_API_URL}/chat/completions
   c. LAMBAPIService.parse_evaluation_response()
      → Extract "NOTA FINAL: X.X" from response
   d. Create grade in database
   ↓
6. Return results to frontend
```

---

## Network Debugging (Docker)

If LAMBA and LAMB are running in different Docker networks:

### Check network connectivity

```bash
# From LAMBA backend container
docker exec -it lamba-backend ping lamb-server-hostname

# Test HTTP connection
docker exec -it lamba-backend curl -v http://lamb.lamb-project.org:9099/v1/models
```

### Check DNS resolution

```bash
docker exec -it lamba-backend nslookup lamb.lamb-project.org
```

### Check if LAMB port is open

```bash
docker exec -it lamba-backend nc -zv lamb.lamb-project.org 9099
```

---

## Quick Checklist

When AI evaluation fails, check:

- [ ] `.env` file has correct `LAMB_API_URL`
- [ ] `.env` file has correct `LAMB_BEARER_TOKEN`
- [ ] LAMB server is running and accessible
- [ ] Activity has `evaluator_id` configured
- [ ] Model `lamb_assistant.{evaluator_id}` exists on LAMB server
- [ ] Network allows connection from LAMBA to LAMB
- [ ] File can be read and text extracted from submission
