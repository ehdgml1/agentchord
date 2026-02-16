#!/usr/bin/env python
"""Test runner script to validate Phase 1 tests."""
import subprocess
import sys


def run_tests():
    """Run all Phase 1 tests."""
    test_files = [
        "tests/test_scheduler.py",
        "tests/test_mock_mode.py",
        "tests/test_resume.py",
        "tests/test_execution_service.py",
    ]

    print("=" * 80)
    print("Running Phase 1 Tests")
    print("=" * 80)

    all_passed = True

    for test_file in test_files:
        print(f"\n{'=' * 80}")
        print(f"Running: {test_file}")
        print("=" * 80)

        result = subprocess.run(
            ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=False,
        )

        if result.returncode != 0:
            all_passed = False
            print(f"\n❌ {test_file} FAILED")
        else:
            print(f"\n✅ {test_file} PASSED")

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ All Phase 1 tests PASSED")
        print("=" * 80)
        return 0
    else:
        print("❌ Some tests FAILED")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
