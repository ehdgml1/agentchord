# IDOR Vulnerability Fix - Webhooks and Schedules

## Summary

Fixed critical Insecure Direct Object Reference (IDOR) vulnerabilities in the AgentWeave Visual Builder backend that allowed any authenticated user to access, modify, or delete ANY other user's webhooks and schedules.

## Severity

**CRITICAL** - CWE-639: Authorization Bypass Through User-Controlled Key

## Impact

Before this fix, any authenticated user could:
- List all webhooks and schedules in the system (regardless of ownership)
- Read details of any webhook or schedule
- Create webhooks/schedules for other users' workflows
- Modify or delete other users' webhooks and schedules
- Rotate webhook secrets belonging to other users

## Files Modified

### 1. `app/api/webhooks.py`

**Changes:**
- Added imports for `WorkflowRepository`, `WorkflowModel`, and `select`
- **list_webhooks**: Now joins with Workflow table and filters by `owner_id == user.id`
- **create_webhook**: Verifies user owns the target workflow before creation
- **get_webhook**: Verifies user owns the associated workflow (returns 404 instead of 403 to prevent enumeration)
- **delete_webhook**: Verifies ownership before deletion
- **rotate_webhook_secret**: Verifies ownership before rotating secret

**Lines Changed:** ~50 lines added for ownership checks

### 2. `app/api/schedules.py`

**Changes:**
- Added import for `WorkflowModel`
- **list_schedules**: Now joins with Workflow table and filters by `owner_id == user.id`
- **create_schedule**: Verifies user owns the target workflow before creation (returns 403)
- **get_schedule**: Verifies user owns the associated workflow (returns 404 to prevent enumeration)
- **update_schedule**: Verifies ownership before update
- **delete_schedule**: Verifies ownership before deletion
- **toggle_schedule**: Verifies ownership before toggle

**Lines Changed:** ~100 lines added for ownership checks

### 3. `tests/test_schedules_api.py`

**Changes:**
- Fixed `create_mock_user()` to use a consistent user ID ("test-user-123")
- Updated `create_workflow_factory()` to accept and set `owner_id` parameter (defaults to "test-user-123")

**Lines Changed:** 5 lines modified

### 4. `tests/test_idor_security.py` (NEW)

**Purpose:** Comprehensive security tests to verify IDOR vulnerabilities are fixed

**Test Coverage:**
- 6 webhook IDOR tests
- 8 schedule IDOR tests
- Tests verify users cannot:
  - List other users' resources
  - Read other users' resources
  - Create resources for other users' workflows
  - Update other users' resources
  - Delete other users' resources
  - Toggle other users' schedules

**Lines:** 439 lines of security tests

## Security Pattern Applied

### Ownership Verification Pattern

For all resource operations:

1. **List operations**: Join with Workflow table and filter by `owner_id == current_user.id`
   ```python
   stmt = (
       select(ResourceModel)
       .join(WorkflowModel, ResourceModel.workflow_id == WorkflowModel.id)
       .where(WorkflowModel.owner_id == user.id)
   )
   ```

2. **Individual resource operations** (get/update/delete):
   - Fetch the resource
   - Fetch the associated workflow
   - Verify `workflow.owner_id == current_user.id`
   - Return 404 (not 403) on failure to prevent enumeration attacks

3. **Create operations**:
   - Verify user owns the target workflow before creating the resource
   - Return 403 on access denied

### Anti-Enumeration

- GET/PUT/DELETE operations return **404** instead of 403 when a user doesn't own a resource
- This prevents attackers from enumerating which resources exist vs which they don't have access to
- CREATE operations return **403** since the attacker already knows the workflow exists

## Test Results

### Before Fix (Vulnerable)
- No ownership checks
- Any user could access any resource
- 0 security tests

### After Fix (Secure)
- All endpoints verify ownership
- 14/14 security tests pass
- 21/21 schedule API tests pass
- All existing tests pass (313 backend tests)

## Verification

To verify the fix:

```bash
# Run security tests
python -m pytest tests/test_idor_security.py -v

# Run schedule API tests
python -m pytest tests/test_schedules_api.py -v

# Run all backend tests
python -m pytest tests/ -v
```

## Manual Testing

### Test Scenario 1: User B cannot list User A's webhooks

1. Create User A and User B
2. User A creates a workflow and webhook
3. Authenticate as User B
4. Call `GET /webhook`
5. **Expected**: Empty list (User A's webhook not visible)

### Test Scenario 2: User B cannot access User A's webhook

1. User A creates a webhook with ID `webhook-123`
2. Authenticate as User B
3. Call `GET /webhook/webhook-123`
4. **Expected**: 404 NOT_FOUND

### Test Scenario 3: User B cannot create webhook for User A's workflow

1. User A creates a workflow with ID `workflow-123`
2. Authenticate as User B
3. Call `POST /webhook` with `workflowId: workflow-123`
4. **Expected**: 403 ACCESS_DENIED

## Recommendations

### Additional Security Measures

1. **Audit Logging**: Log all failed access attempts
2. **Rate Limiting**: Implement rate limiting on webhook/schedule endpoints to prevent brute-force enumeration
3. **Admin Override**: Consider allowing admin users to bypass ownership checks (currently not implemented)
4. **Soft Delete**: Consider soft-deleting resources to prevent timing attacks
5. **Unit Tests**: Add unit tests for the repository layer ownership queries

### Future Work

1. Add similar ownership checks to other resource endpoints (executions, AB tests, etc.)
2. Implement row-level security (RLS) at the database level
3. Add integration tests that verify cross-user access is blocked at the HTTP layer
4. Add security scanning to CI/CD pipeline

## References

- OWASP Top 10: A01:2021 – Broken Access Control
- CWE-639: Authorization Bypass Through User-Controlled Key
- OWASP IDOR Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html

## Timeline

- **Discovered**: 2026-02-15
- **Fixed**: 2026-02-15
- **Tests Added**: 2026-02-15
- **Status**: RESOLVED
