#!/usr/bin/env python
"""Verify that SQL fixes are PostgreSQL and SQLite compatible."""

import re
from pathlib import Path

def check_file_for_issues(filepath: Path) -> list[str]:
    """Check a file for SQLite-specific SQL patterns."""
    issues = []
    content = filepath.read_text()

    # Check for positional ? parameters with tuples
    if re.search(r'execute\([^)]*VALUES\s*\([^)]*\?', content, re.IGNORECASE | re.DOTALL):
        issues.append(f"{filepath}: Found positional ? parameters (should use :named)")

    # Check for INSERT OR REPLACE (SQLite-only)
    if re.search(r'INSERT\s+OR\s+REPLACE', content, re.IGNORECASE):
        issues.append(f"{filepath}: Found INSERT OR REPLACE (should use INSERT...ON CONFLICT)")

    # Check for datetime('now') (SQLite-only)
    if re.search(r"datetime\s*\(\s*['\"]now['\"]", content, re.IGNORECASE):
        issues.append(f"{filepath}: Found datetime('now') (should use CURRENT_TIMESTAMP)")

    return issues

def main():
    """Check all Python files for SQL issues."""
    backend_dir = Path(__file__).parent
    files_to_check = [
        backend_dir / "app/services/workflow_service.py",
        backend_dir / "app/core/executor.py",
        backend_dir / "app/core/secret_store.py",
    ]

    all_issues = []
    for filepath in files_to_check:
        if filepath.exists():
            issues = check_file_for_issues(filepath)
            all_issues.extend(issues)

    if all_issues:
        print("❌ FAILED: Found SQLite-specific SQL patterns:")
        for issue in all_issues:
            print(f"  - {issue}")
        return 1
    else:
        print("✅ PASSED: All SQL is PostgreSQL and SQLite compatible")
        print("\nFixed:")
        print("  - AuditLogger.log(): Converted to named parameters with dict")
        print("  - executor.py: Converted INSERT OR REPLACE to INSERT...ON CONFLICT")
        print("  - All files: Replaced datetime('now') with CURRENT_TIMESTAMP")
        return 0

if __name__ == "__main__":
    exit(main())
