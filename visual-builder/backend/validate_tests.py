#!/usr/bin/env python
"""Validate test files structure and imports."""
import ast
import sys
from pathlib import Path


def validate_test_file(filepath: Path) -> tuple[bool, list[str]]:
    """Validate a test file.

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    try:
        with open(filepath, 'r') as f:
            content = f.read()
            tree = ast.parse(content)
    except SyntaxError as e:
        return False, [f"Syntax error: {e}"]

    # Check for pytest import
    has_pytest = False
    has_asyncio_mark = False
    test_count = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'pytest':
                    has_pytest = True

        if isinstance(node, ast.ImportFrom):
            if node.module == 'pytest':
                has_pytest = True

        if isinstance(node, ast.FunctionDef):
            if node.name.startswith('test_'):
                test_count += 1

                # Check for @pytest.mark.asyncio
                for decorator in node.decorators:
                    if isinstance(decorator, ast.Attribute):
                        if (hasattr(decorator.value, 'attr') and
                            decorator.value.attr == 'mark' and
                            decorator.attr == 'asyncio'):
                            has_asyncio_mark = True
                    elif isinstance(decorator, ast.Name):
                        if decorator.id == 'pytest':
                            has_asyncio_mark = True

    if not has_pytest:
        issues.append("Missing pytest import")

    if test_count == 0:
        issues.append("No test functions found")

    return len(issues) == 0, issues


def main():
    """Validate all test files."""
    test_dir = Path(__file__).parent / "tests"

    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return 1

    test_files = [
        "test_scheduler.py",
        "test_mock_mode.py",
        "test_resume.py",
        "test_execution_service.py",
        "conftest.py",
    ]

    print("=" * 80)
    print("Validating Phase 1 Test Files")
    print("=" * 80)

    all_valid = True

    for filename in test_files:
        filepath = test_dir / filename

        if not filepath.exists():
            print(f"\n❌ {filename}: File not found")
            all_valid = False
            continue

        is_valid, issues = validate_test_file(filepath)

        if is_valid:
            print(f"\n✅ {filename}: Valid")
            # Count lines and tests
            with open(filepath) as f:
                lines = len(f.readlines())
            tree = ast.parse(filepath.read_text())
            test_count = sum(1 for node in ast.walk(tree)
                           if isinstance(node, ast.FunctionDef)
                           and node.name.startswith('test_'))
            print(f"   Lines: {lines}, Tests: {test_count}")
        else:
            print(f"\n❌ {filename}: Invalid")
            for issue in issues:
                print(f"   - {issue}")
            all_valid = False

    print("\n" + "=" * 80)

    if all_valid:
        print("✅ All test files are valid")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Run: pytest tests/ -v")
        print("2. Check coverage: pytest tests/ --cov=app --cov-report=term-missing")
        return 0
    else:
        print("❌ Some test files have issues")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
