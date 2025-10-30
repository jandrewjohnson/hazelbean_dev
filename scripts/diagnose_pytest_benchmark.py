#!/usr/bin/env python3
"""
Diagnostic script to test why pytest benchmark is failing in CI.
This replicates the exact command used by run_performance_benchmarks.py
"""

import subprocess
import sys
import os

print("🔍 Pytest Benchmark Diagnostic")
print("=" * 60)

# Change to project root
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

# Replicate the exact command from run_performance_benchmarks.py
cmd = [
    "python", "-m", "pytest",
    "hazelbean_tests/performance/test_benchmarks.py::TestSimpleBenchmarks::test_array_operations_benchmark",
    "hazelbean_tests/performance/test_functions.py::TestGetPathFunctionBenchmarks::test_get_path_function_overhead",
    "--benchmark-json=test_diagnostic_output.json",
    "-vv",  # Very verbose
    "--tb=short"
]

print(f"\n📋 Command:")
print(" ".join(cmd))
print()

result = subprocess.run(cmd, capture_output=True, text=True)

print(f"\n📊 Results:")
print(f"   Return code: {result.returncode}")
print(f"   Stdout length: {len(result.stdout)} chars")
print(f"   Stderr length: {len(result.stderr)} chars")

if result.stdout:
    print(f"\n📄 STDOUT (first 2000 chars):")
    print(result.stdout[:2000])

if result.stderr:
    print(f"\n⚠️  STDERR (first 2000 chars):")
    print(result.stderr[:2000])

# Check if JSON was created
if os.path.exists("test_diagnostic_output.json"):
    size = os.path.getsize("test_diagnostic_output.json")
    print(f"\n✅ JSON file created: {size} bytes")
    if size == 0:
        print("   ⚠️  WARNING: JSON file is EMPTY!")
    else:
        print("   ✅ JSON file has content")
        # Show first 500 chars
        with open("test_diagnostic_output.json") as f:
            content = f.read()
            print(f"\n   First 500 chars of JSON:")
            print(f"   {content[:500]}")
    # Cleanup
    os.remove("test_diagnostic_output.json")
else:
    print(f"\n❌ JSON file was NOT created")

print("\n" + "=" * 60)
sys.exit(result.returncode)

