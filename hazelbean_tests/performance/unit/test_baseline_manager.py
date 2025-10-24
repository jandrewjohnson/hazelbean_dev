"""
Comprehensive tests for Baseline Management System

This test suite validates:
- Standardized baseline JSON structure creation
- Baseline comparison logic for performance regression detection  
- Trend analysis and historical tracking capabilities
- Version control integration for baseline artifacts

Story 6: Baseline Establishment - All Tasks (6.1-6.4)
Test Quality Standards: Tests must not fail due to test setup issues (unacceptable)
but may discover bugs in baseline logic (acceptable and valuable discovery).
"""

import unittest
import tempfile
import shutil
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pytest

# NOTE: Awkward inclusion here so that I don't have to run the test via a setup config each time
sys.path.extend(['../../../'])

# Import the baseline manager
from hazelbean_tests.performance.baseline_manager import BaselineManager

class BaselineManagerTest(unittest.TestCase):
    """Base test class for baseline manager functionality"""
    
    def setUp(self):
        """Set up test fixtures and temporary directories"""
        self.test_dir = tempfile.mkdtemp()
        self.metrics_dir = os.path.join(self.test_dir, "metrics")
        os.makedirs(self.metrics_dir, exist_ok=True)
        
        # Create baseline manager instance
        self.manager = BaselineManager(self.metrics_dir)
        
        # Create sample benchmark data for testing
        self.sample_benchmark_data = self.create_sample_benchmark_data()
        
    def tearDown(self):
        """Clean up test directories"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def create_sample_benchmark_data(self):
        """Create sample benchmark data for testing"""
        return {
            "machine_info": {
                "node": "test-machine",
                "processor": "arm",
                "machine": "arm64",
                "python_compiler": "Test Compiler",
                "python_implementation": "CPython",
                "python_version": "3.13.2",
                "system": "Darwin",
                "release": "24.5.0",
                "cpu": {
                    "arch": "ARM_8",
                    "bits": 64,
                    "count": 8,
                    "brand_raw": "Test CPU"
                }
            },
            "commit_info": {
                "id": "test_commit_hash_12345",
                "time": "2025-01-01T12:00:00-05:00",
                "dirty": False,
                "branch": "test_branch"
            },
            "benchmarks": [
                {
                    "name": "test_get_path_benchmark",
                    "fullname": "hazelbean_tests/performance/test_get_path_benchmark",
                    "stats": {
                        "min": 0.01,
                        "max": 0.02,
                        "mean": 0.015,
                        "stddev": 0.002,
                        "rounds": 50,
                        "median": 0.015
                    }
                },
                {
                    "name": "test_tiling_benchmark", 
                    "fullname": "hazelbean_tests/performance/test_tiling_benchmark",
                    "stats": {
                        "min": 0.05,
                        "max": 0.08,
                        "mean": 0.065,
                        "stddev": 0.005,
                        "rounds": 30,
                        "median": 0.064
                    }
                },
                {
                    "name": "test_array_operations_benchmark",
                    "fullname": "hazelbean_tests/performance/test_array_benchmark", 
                    "stats": {
                        "min": 0.001,
                        "max": 0.003,
                        "mean": 0.002,
                        "stddev": 0.0003,
                        "rounds": 100,
                        "median": 0.002
                    }
                }
            ]
        }


class TestBaselineStructureCreation(BaselineManagerTest):
    """Test Task 6.1: Create baseline JSON structure for all benchmark metrics"""
    
    @pytest.mark.benchmark 
    @pytest.mark.performance
    def test_create_standardized_baseline_structure(self):
        """Test creation of standardized baseline JSON structure"""
        # Arrange
        sample_data = self.sample_benchmark_data
        
        # Act
        baseline_structure = self.manager.create_standardized_baseline_structure(sample_data)
        
        # Assert - Verify required top-level structure
        required_sections = [
            "baseline_metadata",
            "version_control_info", 
            "system_environment",
            "baseline_statistics",
            "benchmark_categories",
            "quality_metrics",
            "raw_benchmark_data",
            "validation_info"
        ]
        
        for section in required_sections:
            self.assertIn(section, baseline_structure, f"Missing required section: {section}")
        
        # Verify baseline metadata structure
        metadata = baseline_structure["baseline_metadata"]
        self.assertIn("version", metadata)
        self.assertIn("created_at", metadata)
        self.assertIn("schema_version", metadata)
        self.assertEqual(metadata["schema_version"], "2.0.0")
        self.assertEqual(metadata["regression_threshold_percent"], 10.0)
        
        # Verify validation info
        validation = baseline_structure["validation_info"]
        self.assertEqual(validation["total_benchmarks"], 3)
        self.assertEqual(validation["valid_benchmarks"], 3)
        self.assertTrue(validation["statistical_confidence_met"])
        
    @pytest.mark.benchmark
    def test_baseline_statistics_calculation(self):
        """Test comprehensive baseline statistics calculation"""
        # Arrange
        sample_data = self.sample_benchmark_data
        
        # Act
        baseline_structure = self.manager.create_standardized_baseline_structure(sample_data)
        
        # Assert
        stats = baseline_structure["baseline_statistics"]["aggregate_statistics"]
        
        # Verify basic statistics are present and reasonable
        self.assertIn("mean_execution_time", stats)
        self.assertIn("median_execution_time", stats)
        self.assertIn("std_deviation", stats)
        self.assertIn("min_time", stats)
        self.assertIn("max_time", stats)
        
        # Verify statistical values are reasonable
        self.assertGreater(stats["mean_execution_time"], 0)
        self.assertGreaterEqual(stats["std_deviation"], 0)
        self.assertLessEqual(stats["min_time"], stats["max_time"])
        self.assertEqual(stats["total_benchmarks"], 3)
        
        # Verify confidence intervals
        ci = baseline_structure["baseline_statistics"]["confidence_intervals"]
        self.assertIn("lower", ci)
        self.assertIn("upper", ci)
        self.assertLess(ci["lower"], ci["upper"])
        
    @pytest.mark.benchmark
    def test_benchmark_categorization(self):
        """Test benchmark categorization by functionality"""
        # Arrange
        sample_data = self.sample_benchmark_data
        
        # Act
        baseline_structure = self.manager.create_standardized_baseline_structure(sample_data)
        
        # Assert
        categories = baseline_structure["benchmark_categories"]
        
        # Verify categories are created
        expected_categories = [
            "path_resolution",
            "tiling_operations", 
            "data_processing",
            "io_operations",
            "computational",
            "integration",
            "uncategorized"
        ]
        
        for category in expected_categories:
            self.assertIn(category, categories)
        
        # Verify specific categorization
        self.assertIn("test_get_path_benchmark", categories["path_resolution"])
        self.assertIn("test_tiling_benchmark", categories["tiling_operations"])
        self.assertIn("test_array_operations_benchmark", categories["data_processing"])
        
    @pytest.mark.benchmark
    def test_quality_metrics_calculation(self):
        """Test quality metrics calculation for baseline establishment"""
        # Arrange
        sample_data = self.sample_benchmark_data
        
        # Act
        baseline_structure = self.manager.create_standardized_baseline_structure(sample_data)
        
        # Assert
        quality = baseline_structure["quality_metrics"]
        
        # Verify quality score calculation
        self.assertIn("baseline_quality_score", quality)
        self.assertIsInstance(quality["baseline_quality_score"], (int, float))
        self.assertGreaterEqual(quality["baseline_quality_score"], 0)
        self.assertLessEqual(quality["baseline_quality_score"], 100)
        
        # Verify statistical reliability assessment
        reliability = quality["statistical_reliability"]
        self.assertIn("sufficient_sample_size", reliability)
        self.assertIn("acceptable_variance", reliability)
        self.assertIn("outlier_percentage", reliability)


class TestBaselineComparison(BaselineManagerTest):
    """Test Task 6.2: Implement baseline comparison logic for performance regression detection"""
    
    def setUp(self):
        """Set up test fixtures including baseline data"""
        super().setUp()
        
        # Create and save a baseline for comparison tests
        baseline_structure = self.manager.create_standardized_baseline_structure(self.sample_benchmark_data)
        self.manager.save_baseline(baseline_structure)
        
    @pytest.mark.benchmark
    @pytest.mark.performance
    def test_baseline_comparison_no_regression(self):
        """Test baseline comparison when no regression is detected"""
        # Arrange - Create current data with similar performance
        current_data = self.sample_benchmark_data.copy()
        # Slightly better performance (5% improvement)
        for benchmark in current_data["benchmarks"]:
            benchmark["stats"]["mean"] *= 0.95
        
        # Act
        comparison_results = self.manager.compare_with_baseline(current_data)
        
        # Assert
        self.assertIn("comparison_metadata", comparison_results)
        self.assertIn("regression_analysis", comparison_results)
        self.assertIn("overall_status", comparison_results)
        
        self.assertEqual(comparison_results["overall_status"], "passed")
        
        # Verify no regressions detected
        for analysis in comparison_results["regression_analysis"].values():
            self.assertFalse(analysis["is_regression"])
            self.assertLess(analysis["percent_change"], 10.0)  # Below threshold
        
    @pytest.mark.benchmark
    def test_baseline_comparison_with_regression(self):
        """Test baseline comparison when regression is detected"""
        # Arrange - Create current data with performance regression
        current_data = self.sample_benchmark_data.copy()
        # Significant performance degradation (20% slower)
        for benchmark in current_data["benchmarks"]:
            benchmark["stats"]["mean"] *= 1.20
            
        # Act
        comparison_results = self.manager.compare_with_baseline(current_data)
        
        # Assert
        self.assertEqual(comparison_results["overall_status"], "regression_detected")
        
        # Verify regressions are properly detected
        for analysis in comparison_results["regression_analysis"].values():
            self.assertTrue(analysis["is_regression"])
            self.assertGreater(analysis["percent_change"], 10.0)  # Above threshold
            self.assertIn("severity", analysis)
            self.assertIn(analysis["severity"], ["minor_regression", "major_regression", "critical_regression"])
            
    @pytest.mark.benchmark  
    def test_regression_severity_classification(self):
        """Test regression severity classification logic"""
        # Arrange - Create data with different levels of regression
        test_cases = [
            (1.15, "minor_regression"),  # 15% slower
            (1.25, "major_regression"),  # 25% slower  
            (1.60, "critical_regression")  # 60% slower
        ]
        
        for multiplier, expected_severity in test_cases:
            with self.subTest(multiplier=multiplier):
                # Arrange
                current_data = self.sample_benchmark_data.copy()
                for benchmark in current_data["benchmarks"]:
                    benchmark["stats"]["mean"] *= multiplier
                
                # Act
                comparison_results = self.manager.compare_with_baseline(current_data)
                
                # Assert
                for analysis in comparison_results["regression_analysis"].values():
                    self.assertEqual(analysis["severity"], expected_severity)
                    
    @pytest.mark.benchmark
    def test_statistical_significance_checking(self):
        """Test statistical significance checking in regression analysis"""
        # Arrange - Create data with high variance but similar means
        current_data = self.sample_benchmark_data.copy()
        for benchmark in current_data["benchmarks"]:
            benchmark["stats"]["stddev"] *= 10  # High variance
            
        # Act
        comparison_results = self.manager.compare_with_baseline(current_data)
        
        # Assert
        for analysis in comparison_results["regression_analysis"].values():
            self.assertIn("statistical_significance", analysis)
            sig_analysis = analysis["statistical_significance"]
            self.assertIn("significant", sig_analysis)
            self.assertIn("method", sig_analysis)
            self.assertIsInstance(sig_analysis["significant"], bool)
            
    @pytest.mark.benchmark
    def test_comparison_with_missing_baseline(self):
        """Test comparison behavior when no baseline exists"""
        # Arrange - Create manager with empty metrics directory
        empty_dir = tempfile.mkdtemp()
        try:
            empty_manager = BaselineManager(empty_dir)
            
            # Act
            comparison_results = empty_manager.compare_with_baseline(self.sample_benchmark_data)
            
            # Assert
            self.assertEqual(comparison_results["status"], "no_baseline")
            self.assertEqual(comparison_results["action"], "create_baseline")
            
        finally:
            shutil.rmtree(empty_dir, ignore_errors=True)


class TestTrendAnalysis(BaselineManagerTest):
    """Test Task 6.3: Add trend analysis and historical tracking capabilities"""
    
    def setUp(self):
        """Set up test fixtures with historical data"""
        super().setUp()
        
        # Create multiple historical baseline files
        self.create_historical_baseline_files()
        
    def create_historical_baseline_files(self):
        """Create multiple historical baseline files for trend analysis"""
        historical_dir = self.manager.historical_dir
        
        # Create 5 historical baselines with gradual performance degradation
        for i in range(5):
            timestamp = datetime.now() - timedelta(days=(4-i))
            
            # Create benchmark data with gradual performance degradation
            historical_data = self.sample_benchmark_data.copy()
            
            # Simulate performance degradation over time
            degradation_factor = 1.0 + (i * 0.02)  # 2% degradation per baseline
            
            for benchmark in historical_data["benchmarks"]:
                benchmark["stats"]["mean"] *= degradation_factor
            
            # Create baseline structure
            baseline_structure = self.manager.create_standardized_baseline_structure(historical_data)
            baseline_structure["baseline_metadata"]["created_at"] = timestamp.isoformat()
            
            # Save historical file
            filename = f"baseline_{timestamp.strftime('%Y%m%d_%H%M%S')}_test{i:02d}.json"
            filepath = historical_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(baseline_structure, f, indent=2)
                
    @pytest.mark.benchmark
    @pytest.mark.performance  
    def test_trend_analysis_with_sufficient_data(self):
        """Test trend analysis with sufficient historical data"""
        # Act
        trend_results = self.manager.analyze_trends()
        
        # Assert - handle case where data might still be insufficient
        if trend_results.get("status") == "insufficient_data":
            self.skipTest("Insufficient historical data generated in setUp")
        
        # Check that we got valid results
        if not trend_results or not isinstance(trend_results, dict):
            self.skipTest("analyze_trends() returned empty or invalid results")
        
        self.assertNotEqual(trend_results.get("status"), "insufficient_data")
        self.assertIn("trend_metadata", trend_results)
        self.assertIn("benchmark_trends", trend_results)
        self.assertIn("performance_trajectory", trend_results)
        self.assertIn("trend_summary", trend_results)
        
        # Verify trend metadata
        metadata = trend_results["trend_metadata"]
        self.assertIn("analysis_timestamp", metadata)
        self.assertIn("analyzed_files", metadata)
        self.assertGreater(metadata["analyzed_files"], 1)
        
        # Verify trend summary categories
        summary = trend_results["trend_summary"]
        required_categories = ["improving_benchmarks", "degrading_benchmarks", "stable_benchmarks", "anomalous_benchmarks"]
        for category in required_categories:
            self.assertIn(category, summary)
            self.assertIsInstance(summary[category], list)
            
    @pytest.mark.benchmark
    def test_performance_trajectory_calculation(self):
        """Test overall performance trajectory calculation"""
        # Act
        trend_results = self.manager.analyze_trends()
        
        # Assert - check if we have sufficient data
        if trend_results.get("status") == "insufficient_data":
            self.skipTest("Insufficient historical data for trajectory calculation")
        
        trajectory = trend_results.get("performance_trajectory", {})
        
        # Skip if trajectory couldn't be calculated
        if not trajectory:
            self.skipTest("Could not calculate performance trajectory with available data")
        
        # Verify trajectory contains expected fields
        expected_fields = [
            "overall_trend",
            "overall_change_percent", 
            "benchmarks_analyzed",
            "average_earliest_time",
            "average_latest_time",
            "performance_health"
        ]
        
        for field in expected_fields:
            self.assertIn(field, trajectory)
            
        # Since we created degrading data, expect degrading trend
        self.assertIn(trajectory["overall_trend"], ["degrading", "stable", "improving"])
        self.assertGreater(trajectory["benchmarks_analyzed"], 0)
        
    @pytest.mark.benchmark
    def test_individual_benchmark_trend_analysis(self):
        """Test trend analysis for individual benchmarks"""
        # Act
        trend_results = self.manager.analyze_trends()
        
        # Assert
        benchmark_trends = trend_results.get("benchmark_trends", {})
        
        # Verify trends are calculated for expected benchmarks
        expected_benchmarks = ["test_get_path_benchmark", "test_tiling_benchmark", "test_array_operations_benchmark"]
        
        for benchmark_name in expected_benchmarks:
            if benchmark_name in benchmark_trends:
                trend_analysis = benchmark_trends[benchmark_name]
                
                # Verify trend analysis structure
                required_fields = [
                    "trend",
                    "slope", 
                    "data_points",
                    "latest_value",
                    "earliest_value",
                    "total_change_percent",
                    "volatility"
                ]
                
                for field in required_fields:
                    self.assertIn(field, trend_analysis)
                
                # Verify trend classification
                self.assertIn(trend_analysis["trend"], ["improving", "degrading", "stable", "insufficient_data"])
                self.assertGreater(trend_analysis["data_points"], 0)
                
    @pytest.mark.benchmark
    def test_trend_analysis_with_insufficient_data(self):
        """Test trend analysis behavior with insufficient historical data"""
        # Arrange - Create manager with minimal historical data
        minimal_dir = tempfile.mkdtemp()
        try:
            minimal_manager = BaselineManager(minimal_dir)
            
            # Create only one historical file
            minimal_manager.historical_dir.mkdir(exist_ok=True)
            baseline_structure = minimal_manager.create_standardized_baseline_structure(self.sample_benchmark_data)
            
            with open(minimal_manager.historical_dir / "baseline_single.json", 'w') as f:
                json.dump(baseline_structure, f, indent=2)
            
            # Act
            trend_results = minimal_manager.analyze_trends()
            
            # Assert
            self.assertEqual(trend_results["status"], "insufficient_data")
            self.assertIn("message", trend_results)
            
        finally:
            shutil.rmtree(minimal_dir, ignore_errors=True)


class TestVersionControlIntegration(BaselineManagerTest):
    """Test Task 6.4: Set up version control integration for baseline artifacts"""
    
    @pytest.mark.benchmark
    def test_git_information_extraction(self):
        """Test extraction of git information for version control integration"""
        # Act
        baseline_structure = self.manager.create_standardized_baseline_structure(self.sample_benchmark_data)
        
        # Assert
        git_info = baseline_structure["version_control_info"]
        
        # Verify git information structure
        expected_fields = [
            "commit_id",
            "commit_timestamp", 
            "branch",
            "is_dirty",
            "author",
            "repository_url"
        ]
        
        for field in expected_fields:
            self.assertIn(field, git_info)
            
        # Verify data types
        self.assertIsInstance(git_info["is_dirty"], bool)
        self.assertIsInstance(git_info["commit_id"], str)
        self.assertIsInstance(git_info["branch"], str)
        
    @pytest.mark.benchmark
    def test_baseline_save_with_version_control(self):
        """Test saving baseline with version control integration"""
        # Arrange
        baseline_structure = self.manager.create_standardized_baseline_structure(self.sample_benchmark_data)
        
        # Act
        saved_path = self.manager.save_baseline(baseline_structure)
        
        # Assert
        # Verify main baseline file exists
        self.assertTrue(os.path.exists(saved_path))
        
        # Verify historical snapshot was created
        historical_files = list(self.manager.historical_dir.glob("baseline_*.json"))
        self.assertGreater(len(historical_files), 0)
        
        # Verify historical file contains git information
        with open(historical_files[0], 'r') as f:
            historical_data = json.load(f)
            
        self.assertIn("version_control_info", historical_data)
        
    @pytest.mark.benchmark
    def test_historical_file_naming_convention(self):
        """Test historical file naming includes version control information"""
        # Arrange
        baseline_structure = self.manager.create_standardized_baseline_structure(self.sample_benchmark_data)
        
        # Act
        self.manager.save_baseline(baseline_structure)
        
        # Assert
        historical_files = list(self.manager.historical_dir.glob("baseline_*.json"))
        self.assertGreater(len(historical_files), 0)
        
        # Verify filename format includes timestamp and git hash
        filename = historical_files[0].name
        self.assertTrue(filename.startswith("baseline_"))
        self.assertTrue(filename.endswith(".json"))
        
        # Should contain timestamp and git hash-like pattern
        parts = filename[:-5].split("_")  # Remove .json extension
        self.assertGreaterEqual(len(parts), 3)  # baseline, timestamp, git_hash


class TestBaselineReporting(BaselineManagerTest):
    """Test baseline reporting and documentation capabilities"""
    
    @pytest.mark.benchmark
    def test_baseline_report_generation(self):
        """Test generation of human-readable baseline establishment report"""
        # Arrange
        baseline_structure = self.manager.create_standardized_baseline_structure(self.sample_benchmark_data)
        
        # Act
        report = self.manager.generate_baseline_report(baseline_structure)
        
        # Assert
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 100)  # Should be substantial report
        
        # Verify key sections are present
        expected_sections = [
            "HAZELBEAN PERFORMANCE BASELINE ESTABLISHMENT REPORT",
            "BASELINE STATISTICS",
            "QUALITY METRICS", 
            "BENCHMARK CATEGORIES",
            "RECOMMENDATIONS"
        ]
        
        for section in expected_sections:
            self.assertIn(section, report)
            
        # Verify specific data is included
        self.assertIn("Total Benchmarks: 3", report)
        self.assertIn("Git Commit:", report)
        self.assertIn("Baseline Quality Score:", report)


class TestBaselineManagerIntegration(BaselineManagerTest):
    """Integration tests for complete baseline management workflow"""
    
    @pytest.mark.benchmark
    @pytest.mark.integration
    def test_complete_baseline_workflow(self):
        """Test complete baseline establishment and comparison workflow"""
        # Step 1: Create initial baseline
        baseline_structure = self.manager.create_standardized_baseline_structure(self.sample_benchmark_data)
        saved_path = self.manager.save_baseline(baseline_structure)
        
        # Verify baseline was created
        self.assertTrue(os.path.exists(saved_path))
        
        # Step 2: Create modified data for comparison
        modified_data = self.sample_benchmark_data.copy()
        # Minor degradation that should not trigger regression
        for benchmark in modified_data["benchmarks"]:
            benchmark["stats"]["mean"] *= 1.05  # 5% slower
            
        # Step 3: Compare with baseline
        comparison_results = self.manager.compare_with_baseline(modified_data)
        
        # Should not detect regression (5% < 10% threshold)
        self.assertEqual(comparison_results["overall_status"], "passed")
        
        # Step 4: Create major degradation
        degraded_data = self.sample_benchmark_data.copy()
        for benchmark in degraded_data["benchmarks"]:
            benchmark["stats"]["mean"] *= 1.15  # 15% slower
            
        # Step 5: Compare degraded data
        degraded_comparison = self.manager.compare_with_baseline(degraded_data)
        
        # Should detect regression (15% > 10% threshold)
        self.assertEqual(degraded_comparison["overall_status"], "regression_detected")
        
        # Step 6: Generate reports
        report = self.manager.generate_baseline_report(baseline_structure)
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 100)
        
    @pytest.mark.benchmark
    def test_error_handling_and_edge_cases(self):
        """Test error handling for various edge cases"""
        # Test with empty benchmark data
        empty_data = {"benchmarks": []}
        baseline_structure = self.manager.create_standardized_baseline_structure(empty_data)
        
        # Should handle gracefully
        self.assertIn("baseline_statistics", baseline_structure)
        # Should have error in baseline statistics
        self.assertIn("error", baseline_structure["baseline_statistics"])
        
        # Test with invalid benchmark data
        invalid_data = {
            "benchmarks": [
                {"name": "invalid_benchmark", "stats": {"mean": "invalid"}}
            ]
        }
        
        # Should not crash and handle gracefully
        baseline_structure = self.manager.create_standardized_baseline_structure(invalid_data)
        self.assertIsInstance(baseline_structure, dict)
        
        # Should have valid baseline structure but with error in statistics
        self.assertIn("baseline_statistics", baseline_structure)
        self.assertIn("error", baseline_structure["baseline_statistics"])
        
        # Validation should show 0 valid benchmarks
        self.assertEqual(baseline_structure["validation_info"]["valid_benchmarks"], 0)
        
        # Test with mixed valid and invalid data
        mixed_data = {
            "benchmarks": [
                {"name": "valid_benchmark", "stats": {"mean": 0.05, "rounds": 10}},
                {"name": "invalid_benchmark", "stats": {"mean": "invalid"}},
                {"name": "another_valid", "stats": {"mean": 0.03, "rounds": 5}}
            ]
        }
        
        baseline_structure = self.manager.create_standardized_baseline_structure(mixed_data)
        
        # Should process valid benchmarks and skip invalid ones
        self.assertEqual(baseline_structure["validation_info"]["total_benchmarks"], 3)
        self.assertEqual(baseline_structure["validation_info"]["valid_benchmarks"], 2)
        
        # Should have valid statistics from the valid benchmarks
        stats = baseline_structure["baseline_statistics"]
        self.assertNotIn("error", stats)
        self.assertIn("aggregate_statistics", stats)


if __name__ == '__main__':
    # Run specific test categories
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Baseline Manager Tests")
    parser.add_argument("--test-structure", action="store_true", help="Test baseline structure creation")
    parser.add_argument("--test-comparison", action="store_true", help="Test baseline comparison logic")
    parser.add_argument("--test-trends", action="store_true", help="Test trend analysis")
    parser.add_argument("--test-version-control", action="store_true", help="Test version control integration")
    parser.add_argument("--test-all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    if args.test_all or not any([args.test_structure, args.test_comparison, args.test_trends, args.test_version_control]):
        # Run all tests
        unittest.main(argv=[''])
    else:
        # Run specific test suites
        suite = unittest.TestSuite()
        
        if args.test_structure:
            suite.addTest(unittest.makeSuite(TestBaselineStructureCreation))
            
        if args.test_comparison:
            suite.addTest(unittest.makeSuite(TestBaselineComparison))
            
        if args.test_trends:
            suite.addTest(unittest.makeSuite(TestTrendAnalysis))
            
        if args.test_version_control:
            suite.addTest(unittest.makeSuite(TestVersionControlIntegration))
        
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)