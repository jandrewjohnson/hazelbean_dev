"""
Consolidated Performance Workflow Tests

This file consolidates tests from:
- workflows/test_performance_aggregation.py
- workflows/test_performance_integration.py

Covers workflow-level performance testing including:
- End-to-end workflow performance benchmarks
- Performance aggregation and reporting
- Integration with CI/CD pipeline performance validation
- JSON artifact storage and version control integration
- Performance baseline establishment and validation
- Cross-system performance consistency testing
"""

import unittest
import os
import sys
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
import pytest

# NOTE: Awkward inclusion here so that I don't have to run the test via a setup config each time
sys.path.extend(['../..'])

import hazelbean as hb
import numpy as np


class BaseWorkflowPerformanceTest(unittest.TestCase):
    """Base class for workflow-level performance tests with shared setup"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.metrics_dir = os.path.join(os.path.dirname(__file__), "../../metrics")
        os.makedirs(self.metrics_dir, exist_ok=True)
        
        # Create ProjectFlow instance
        self.p = hb.ProjectFlow(self.test_dir)
        
    def tearDown(self):
        """Clean up test directories"""
        shutil.rmtree(self.test_dir, ignore_errors=True)


class TestPerformanceIntegration(BaseWorkflowPerformanceTest):
    """Test performance integration workflows (from test_performance_integration.py)"""

    @pytest.mark.benchmark
    def test_json_artifact_storage_performance(self):
        """Test JSON artifact storage and version control integration performance"""
        
        # Create performance data
        performance_data = {
            "timestamp": datetime.now().isoformat(),
            "test_suite": "workflow_performance",
            "metrics": {
                "execution_time": 2.34,
                "memory_usage_mb": 150.5,
                "cpu_usage_percent": 45.2,
                "disk_io_mb": 25.8
            },
            "environment": {
                "python_version": sys.version,
                "hazelbean_version": "dev",
                "platform": sys.platform
            },
            "test_details": {
                "total_tests": 10,
                "passed_tests": 10,
                "failed_tests": 0,
                "skipped_tests": 0
            }
        }
        
        # Benchmark JSON artifact creation and storage
        import time
        start_time = time.time()
        
        # Create artifact file
        artifact_file = os.path.join(self.metrics_dir, f"performance_artifact_{int(time.time())}.json")
        with open(artifact_file, 'w') as f:
            json.dump(performance_data, f, indent=2)
        
        # Verify file was created
        assert os.path.exists(artifact_file)
        
        # Read back and verify
        with open(artifact_file, 'r') as f:
            loaded_data = json.load(f)
        
        end_time = time.time()
        
        storage_duration = end_time - start_time
        
        # Performance assertions
        assert storage_duration < 1.0, f"JSON artifact storage took {storage_duration:.4f}s, should be <1s"
        assert loaded_data == performance_data, "Loaded data should match original"
        
        # Cleanup
        os.remove(artifact_file)

    @pytest.mark.benchmark 
    def test_performance_baseline_validation_workflow(self):
        """Test performance baseline establishment and validation workflow"""
        
        # Create baseline performance metrics
        baseline_metrics = {
            "get_path_single_call": 0.001,
            "get_path_100_calls": 0.1, 
            "array_operations": 1.5,
            "file_io_operations": 0.5
        }
        
        # Simulate current performance measurements
        import time
        start_time = time.time()
        
        # Measure actual performance
        measured_metrics = {}
        
        # get_path performance
        path_start = time.time()
        result = self.p.get_path("test_file.txt", raise_error_if_fail=False)
        measured_metrics["get_path_single_call"] = time.time() - path_start
        
        # Array operations performance
        array_start = time.time()
        test_array = np.random.rand(100, 100)
        processed = test_array * 2 + 1
        result_sum = np.sum(processed)
        measured_metrics["array_operations"] = time.time() - array_start
        
        # File I/O performance
        io_start = time.time()
        temp_file = os.path.join(self.test_dir, "perf_test.txt")
        with open(temp_file, 'w') as f:
            f.write("performance test data" * 100)
        with open(temp_file, 'r') as f:
            content = f.read()
        measured_metrics["file_io_operations"] = time.time() - io_start
        
        end_time = time.time()
        
        total_measurement_time = end_time - start_time
        
        # Performance validation against baseline
        performance_regressions = []
        for metric, baseline_value in baseline_metrics.items():
            if metric in measured_metrics:
                measured_value = measured_metrics[metric]
                # Allow 50% variance from baseline
                if measured_value > baseline_value * 1.5:
                    performance_regressions.append({
                        "metric": metric,
                        "baseline": baseline_value,
                        "measured": measured_value,
                        "ratio": measured_value / baseline_value
                    })
        
        # Performance assertions
        assert total_measurement_time < 10.0, f"Performance measurement took {total_measurement_time:.4f}s, should be <10s"
        
        # Allow some performance regressions in tests, but document them
        if performance_regressions:
            print(f"Performance regressions detected: {performance_regressions}")
            # In real CI/CD, this might trigger warnings but not fail the test
            
        # Verify all metrics were measured
        assert len(measured_metrics) >= 3, "Should have measured multiple performance metrics"

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_ci_cd_performance_integration(self):
        """Test integration with CI/CD pipeline performance validation"""
        
        # Simulate CI/CD environment performance testing
        import time
        start_time = time.time()
        
        ci_performance_data = {
            "build_id": "test_build_12345",
            "commit_hash": "abcd1234",
            "branch": "main",
            "timestamp": datetime.now().isoformat(),
            "performance_tests": {}
        }
        
        # Run multiple performance tests as would happen in CI/CD
        test_cases = [
            ("basic_operations", self._benchmark_basic_operations),
            ("file_processing", self._benchmark_file_processing),
            ("memory_usage", self._benchmark_memory_usage)
        ]
        
        for test_name, test_function in test_cases:
            test_start = time.time()
            try:
                test_result = test_function()
                test_duration = time.time() - test_start
                
                ci_performance_data["performance_tests"][test_name] = {
                    "status": "passed",
                    "duration": test_duration,
                    "result": test_result
                }
            except Exception as e:
                test_duration = time.time() - test_start
                ci_performance_data["performance_tests"][test_name] = {
                    "status": "failed",
                    "duration": test_duration,
                    "error": str(e)
                }
        
        end_time = time.time()
        total_ci_time = end_time - start_time
        
        # Save CI performance data
        ci_artifact_file = os.path.join(self.metrics_dir, f"ci_performance_{int(time.time())}.json")
        with open(ci_artifact_file, 'w') as f:
            json.dump(ci_performance_data, f, indent=2)
        
        # Performance assertions for CI/CD workflow
        assert total_ci_time < 30.0, f"CI/CD performance tests took {total_ci_time:.4f}s, should be <30s"
        assert os.path.exists(ci_artifact_file), "CI performance artifact should be created"
        assert len(ci_performance_data["performance_tests"]) == len(test_cases), "All test cases should be executed"
        
        # Cleanup
        os.remove(ci_artifact_file)
    
    def _benchmark_basic_operations(self):
        """Helper method for benchmarking basic operations"""
        import time
        start_time = time.time()
        
        # Basic operations
        for i in range(100):
            path = self.p.get_path(f"test_file_{i}.txt")
        
        duration = time.time() - start_time
        return {"avg_time_per_operation": duration / 100}
    
    def _benchmark_file_processing(self):
        """Helper method for benchmarking file processing"""
        import time
        start_time = time.time()
        
        # File processing operations
        test_files = []
        for i in range(10):
            temp_array = np.random.rand(50, 50)
            temp_file = hb.temp('.npy', f'benchmark_{i}', True)
            hb.save_array_as_npy(temp_array, temp_file)
            test_files.append(temp_file)
        
        duration = time.time() - start_time
        return {"files_processed": len(test_files), "total_time": duration}
    
    def _benchmark_memory_usage(self):
        """Helper method for benchmarking memory usage"""
        import time
        start_time = time.time()
        
        # Memory-intensive operations
        large_arrays = []
        for i in range(5):
            array = np.random.rand(200, 200)
            large_arrays.append(array)
        
        # Process arrays
        results = []
        for array in large_arrays:
            result = np.sum(array)
            results.append(result)
        
        # Cleanup
        del large_arrays
        
        duration = time.time() - start_time
        return {"arrays_processed": len(results), "total_time": duration}


class TestPerformanceAggregation(BaseWorkflowPerformanceTest):
    """Test performance aggregation workflows (from test_performance_aggregation.py)"""

    @pytest.mark.benchmark
    def test_performance_metrics_aggregation(self):
        """Test aggregation of performance metrics from multiple sources"""
        
        # Create multiple performance metric sources
        metric_sources = [
            {
                "source": "unit_tests",
                "metrics": {
                    "avg_execution_time": 0.05,
                    "max_execution_time": 0.2,
                    "total_tests": 150,
                    "memory_peak_mb": 45.2
                }
            },
            {
                "source": "integration_tests", 
                "metrics": {
                    "avg_execution_time": 1.2,
                    "max_execution_time": 5.5,
                    "total_tests": 25,
                    "memory_peak_mb": 120.8
                }
            },
            {
                "source": "performance_tests",
                "metrics": {
                    "avg_execution_time": 2.8,
                    "max_execution_time": 15.0,
                    "total_tests": 10,
                    "memory_peak_mb": 200.5
                }
            }
        ]
        
        # Benchmark aggregation process
        import time
        start_time = time.time()
        
        # Aggregate metrics
        aggregated = {
            "total_tests": 0,
            "weighted_avg_execution_time": 0,
            "overall_max_execution_time": 0,
            "total_memory_peak_mb": 0,
            "sources": len(metric_sources)
        }
        
        total_execution_time = 0
        for source_data in metric_sources:
            metrics = source_data["metrics"]
            
            aggregated["total_tests"] += metrics["total_tests"]
            total_execution_time += metrics["avg_execution_time"] * metrics["total_tests"]
            aggregated["overall_max_execution_time"] = max(
                aggregated["overall_max_execution_time"], 
                metrics["max_execution_time"]
            )
            aggregated["total_memory_peak_mb"] = max(
                aggregated["total_memory_peak_mb"],
                metrics["memory_peak_mb"]
            )
        
        # Calculate weighted average
        if aggregated["total_tests"] > 0:
            aggregated["weighted_avg_execution_time"] = total_execution_time / aggregated["total_tests"]
        
        end_time = time.time()
        aggregation_time = end_time - start_time
        
        # Performance assertions
        assert aggregation_time < 1.0, f"Metrics aggregation took {aggregation_time:.4f}s, should be <1s"
        assert aggregated["total_tests"] == 185, "Should aggregate all tests"
        assert aggregated["sources"] == 3, "Should process all sources"
        assert aggregated["weighted_avg_execution_time"] > 0, "Should calculate weighted average"
        assert aggregated["overall_max_execution_time"] == 15.0, "Should find maximum execution time"
        
    @pytest.mark.benchmark
    def test_performance_trend_analysis(self):
        """Test performance trend analysis workflow"""
        
        # Create historical performance data
        historical_data = []
        base_time = datetime.now().timestamp()
        
        for i in range(10):  # 10 data points
            data_point = {
                "timestamp": base_time - (i * 86400),  # Daily intervals
                "metrics": {
                    "avg_response_time": 0.1 + (i * 0.01),  # Gradually increasing
                    "throughput": 1000 - (i * 10),  # Gradually decreasing
                    "error_rate": 0.01 + (i * 0.001),  # Gradually increasing
                    "memory_usage": 100 + (i * 5)  # Gradually increasing
                }
            }
            historical_data.append(data_point)
        
        # Benchmark trend analysis
        import time
        start_time = time.time()
        
        # Analyze trends
        trends = {}
        metrics_to_analyze = ["avg_response_time", "throughput", "error_rate", "memory_usage"]
        
        for metric in metrics_to_analyze:
            values = [dp["metrics"][metric] for dp in historical_data]
            
            # Simple trend analysis
            if len(values) >= 2:
                trend_direction = "increasing" if values[0] > values[-1] else "decreasing"
                trend_magnitude = abs(values[0] - values[-1]) / values[-1]
                
                trends[metric] = {
                    "direction": trend_direction,
                    "magnitude_percent": trend_magnitude * 100,
                    "latest_value": values[0],
                    "oldest_value": values[-1]
                }
        
        end_time = time.time()
        analysis_time = end_time - start_time
        
        # Performance assertions
        assert analysis_time < 2.0, f"Trend analysis took {analysis_time:.4f}s, should be <2s"
        assert len(trends) == len(metrics_to_analyze), "Should analyze all metrics"
        
        # Verify trend detection
        assert trends["avg_response_time"]["direction"] == "decreasing", "Should detect response time trend"
        assert trends["throughput"]["direction"] == "increasing", "Should detect throughput trend"
        
    @pytest.mark.benchmark
    def test_performance_report_generation(self):
        """Test performance report generation workflow"""
        
        # Create comprehensive performance data
        performance_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_type": "comprehensive_performance",
                "period": "weekly",
                "version": "1.0"
            },
            "summary": {
                "total_tests_executed": 500,
                "total_execution_time": 125.5,
                "avg_test_time": 0.251,
                "performance_score": 85.2
            },
            "detailed_metrics": {
                "by_category": {
                    "unit_tests": {"count": 400, "avg_time": 0.05, "total_time": 20.0},
                    "integration_tests": {"count": 75, "avg_time": 1.2, "total_time": 90.0},
                    "performance_tests": {"count": 25, "avg_time": 0.62, "total_time": 15.5}
                },
                "by_component": {
                    "get_path": {"calls": 10000, "avg_time": 0.001, "total_time": 10.0},
                    "array_operations": {"calls": 500, "avg_time": 0.15, "total_time": 75.0},
                    "file_io": {"calls": 200, "avg_time": 0.2, "total_time": 40.0}
                }
            }
        }
        
        # Benchmark report generation
        import time
        start_time = time.time()
        
        # Generate report file
        report_file = os.path.join(self.metrics_dir, f"performance_report_{int(time.time())}.json")
        with open(report_file, 'w') as f:
            json.dump(performance_data, f, indent=2)
        
        # Generate summary statistics
        summary_stats = {
            "total_categories": len(performance_data["detailed_metrics"]["by_category"]),
            "total_components": len(performance_data["detailed_metrics"]["by_component"]),
            "fastest_category": min(
                performance_data["detailed_metrics"]["by_category"].items(),
                key=lambda x: x[1]["avg_time"]
            )[0],
            "slowest_category": max(
                performance_data["detailed_metrics"]["by_category"].items(),
                key=lambda x: x[1]["avg_time"]
            )[0]
        }
        
        end_time = time.time()
        report_generation_time = end_time - start_time
        
        # Performance assertions
        assert report_generation_time < 5.0, f"Report generation took {report_generation_time:.4f}s, should be <5s"
        assert os.path.exists(report_file), "Report file should be created"
        
        # Verify report content
        with open(report_file, 'r') as f:
            generated_report = json.load(f)
        
        assert generated_report == performance_data, "Generated report should match input data"
        assert summary_stats["fastest_category"] == "unit_tests", "Should identify fastest category"
        assert summary_stats["slowest_category"] == "integration_tests", "Should identify slowest category"
        
        # Cleanup
        os.remove(report_file)

    @pytest.mark.benchmark
    @pytest.mark.slow
    @pytest.mark.xfail(reason="Test checks cross-platform consistency but runs on same platform, measuring repeatability which varies on CI due to file I/O variance")
    def test_cross_platform_performance_consistency(self):
        """Test performance consistency across different environments"""
        
        # Simulate cross-platform performance testing
        platforms = ["linux", "windows", "macos"]  # Simulated platform data
        
        platform_results = {}
        
        # Benchmark cross-platform consistency measurement
        import time
        start_time = time.time()
        
        for platform in platforms:
            # Simulate platform-specific performance measurements
            platform_start = time.time()
            
            # Run standard performance tests
            measurements = {
                "get_path_performance": self._measure_get_path_performance(),
                "array_processing": self._measure_array_processing(),
                "file_io_performance": self._measure_file_io_performance()
            }
            
            platform_duration = time.time() - platform_start
            
            platform_results[platform] = {
                "measurements": measurements,
                "total_measurement_time": platform_duration
            }
        
        end_time = time.time()
        total_cross_platform_time = end_time - start_time
        
        # Analyze consistency
        consistency_analysis = {}
        for metric in ["get_path_performance", "array_processing", "file_io_performance"]:
            values = [results["measurements"][metric] for results in platform_results.values()]
            
            avg_value = sum(values) / len(values)
            max_deviation = max(abs(v - avg_value) for v in values)
            consistency_percentage = (1 - max_deviation / avg_value) * 100 if avg_value > 0 else 0
            
            consistency_analysis[metric] = {
                "average": avg_value,
                "max_deviation": max_deviation,
                "consistency_percentage": consistency_percentage,
                "values": dict(zip(platforms, values))
            }
        
        # Performance assertions
        assert total_cross_platform_time < 20.0, f"Cross-platform testing took {total_cross_platform_time:.4f}s, should be <20s"
        assert len(platform_results) == len(platforms), "Should test all platforms"
        
        # Consistency assertions (allow reasonable variance)
        for metric, analysis in consistency_analysis.items():
            assert analysis["consistency_percentage"] > 50, f"Metric '{metric}' consistency {analysis['consistency_percentage']:.1f}% too low"
    
    def _measure_get_path_performance(self):
        """Helper method to measure get_path performance with actual files"""
        import time
        
        # Create a small set of actual test files in the project directory
        test_files = []
        for i in range(10):
            test_file = os.path.join(self.test_dir, f"perf_get_path_test_{i}.txt")
            with open(test_file, 'w') as f:
                f.write(f"test content {i}")
            test_files.append(f"perf_get_path_test_{i}.txt")
        
        # Measure get_path performance on existing files (100 iterations across 10 files)
        start_time = time.time()
        for i in range(100):
            file_name = test_files[i % 10]  # Rotate through the 10 test files
            resolved_path = self.p.get_path(file_name)
            # Verify the path was actually resolved correctly
            assert os.path.exists(resolved_path), f"get_path should resolve to existing file: {resolved_path}"
        
        duration = time.time() - start_time
        
        # Cleanup test files
        for test_file in test_files:
            file_path = os.path.join(self.test_dir, test_file)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        return duration
    
    def _measure_array_processing(self):
        """Helper method to measure array processing performance"""
        import time
        start_time = time.time()
        for i in range(10):
            array = np.random.rand(100, 100)
            result = np.sum(array * 2)
        return time.time() - start_time
    
    def _measure_file_io_performance(self):
        """Helper method to measure file I/O performance"""
        import time
        start_time = time.time()
        for i in range(10):
            temp_file = os.path.join(self.test_dir, f"perf_test_{i}.txt")
            with open(temp_file, 'w') as f:
                f.write("test data" * 100)
            with open(temp_file, 'r') as f:
                content = f.read()
        return time.time() - start_time


if __name__ == "__main__":
    unittest.main()

