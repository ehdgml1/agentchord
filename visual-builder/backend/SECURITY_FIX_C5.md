# Security Fix: Issue C5 - Debug WebSocket IDOR Vulnerability

## Vulnerability Description
The debug WebSocket endpoint (`/ws/debug/{workflow_id}`) authenticated users via JWT token but did NOT verify that the authenticated user owned the workflow being debugged. This allowed any authenticated user to debug any other user's workflow (Insecure Direct Object Reference - IDOR).

## Severity
**CRITICAL** - Allows unauthorized access to other users' workflows, potentially exposing sensitive data and business logic.

## Files Modified
- `app/api/debug_ws.py`

## Changes Made

### 1. Added user_payload parameter to _run_debug_workflow()
**Lines 238-243, 252**: Added `user_payload: dict` parameter to pass authenticated user info to the workflow execution function.

**Lines 179-186**: Updated the `debug_workflow` WebSocket handler to pass `user_payload` to `_run_debug_workflow()`.

### 2. Added ownership verification
**Lines 276-283**: After loading the workflow from the database, added ownership verification logic:

```python
# Verify ownership (IDOR protection)
user_id = user_payload.get("sub")
user_role = user_payload.get("role")

# Check ownership: allow if admin, or if owner_id is None (legacy), or if user owns it
if workflow.owner_id is not None and user_role != "admin" and workflow.owner_id != user_id:
    await websocket.close(code=4003, reason="Not authorized to debug this workflow")
    return
```

## Access Control Logic

The ownership check implements the following rules:

1. **Owner Access**: User with `user_id == workflow.owner_id` can debug the workflow
2. **Admin Bypass**: Users with `role == "admin"` can debug any workflow
3. **Legacy Workflows**: Workflows with `owner_id = None` are accessible (backward compatibility)
4. **Unauthorized**: All other cases close the WebSocket with code `4003` and reason "Not authorized to debug this workflow"

## Security Properties

- **Defense in Depth**: Adds a second layer of authorization after authentication
- **Principle of Least Privilege**: Users can only debug their own workflows (unless admin)
- **Fail-Safe**: If `user_id` is missing from JWT payload, access is denied
- **Backward Compatible**: Legacy workflows (without owner_id) remain accessible
- **Clear Error Messages**: Returns specific WebSocket close code (4003) for unauthorized access

## Testing

Created comprehensive test suite in `tests/test_debug_ws_security.py`:

- `test_owner_can_debug_workflow` - Verifies owner access
- `test_non_owner_cannot_debug_workflow` - Verifies IDOR protection
- `test_admin_can_debug_any_workflow` - Verifies admin bypass
- `test_legacy_workflow_without_owner` - Verifies backward compatibility
- `test_workflow_not_found` - Verifies error handling
- `test_user_payload_missing_sub` - Verifies graceful handling of malformed JWT
- `test_user_payload_missing_role` - Verifies graceful handling of missing role

## Verification

To verify the fix:

1. **Run new security tests**:
   ```bash
   pytest tests/test_debug_ws_security.py -v
   ```

2. **Run full test suite**:
   ```bash
   pytest tests/ -v
   ```

3. **Manual testing**:
   - Create workflow as user A
   - Attempt to debug as user B (should fail with 4003)
   - Attempt to debug as admin (should succeed)
   - Attempt to debug as user A (should succeed)

## Deployment Notes

- **No Database Migration Required**: Uses existing `owner_id` field in Workflow model
- **No Breaking Changes**: Only adds additional authorization check
- **WebSocket Close Code**: Clients should handle close code `4003` as "Forbidden/Unauthorized"

## Related Issues
- Issue C5: Debug WebSocket Missing Ownership Check (CRITICAL)
- Related to overall IDOR vulnerability remediation effort

## Date Fixed
2026-02-15
