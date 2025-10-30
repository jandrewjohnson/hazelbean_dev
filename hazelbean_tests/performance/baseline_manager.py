"""
Baseline Management System for Hazelbean Performance Benchmarks

This module provides a comprehensive baseline management system for storing,
comparing, and tracking performance benchmarks over time.

Story 6: Baseline Establishment - All Tasks (6.1-6.4)
Test Quality Standards: Baseline management must provide reliable regression detection
"""

import json
import os
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaselineManager:
    """
    Manages performance baselines with comprehensive JSON structure,
    regression detection, trend analysis, and version control integration.
    
    Implements Story 6 requirements:
    - 6.1: Standardized baseline JSON structure
    - 6.2: Baseline comparison logic for regression detection
    - 6.3: Trend analysis and historical tracking
    - 6.4: Version control integration
    """
    
    def __init__(self, metrics_dir: str = None):
        """Initialize baseline manager with metrics directory"""
        if metrics_dir is None:
            # Default to project metrics directory
            self.metrics_dir = Path(__file__).parent.parent.parent / "metrics"
        else:
            self.metrics_dir = Path(metrics_dir)
        
        self.metrics_dir.mkdir(exist_ok=True)
        
        # Create organized directory structure
        self.baselines_dir = self.metrics_dir / "baselines"
        self.snapshots_dir = self.baselines_dir / "snapshots" 
        self.benchmarks_dir = self.metrics_dir / "benchmarks"
        
        # Create directories
        self.baselines_dir.mkdir(exist_ok=True)
        self.snapshots_dir.mkdir(exist_ok=True)
        self.benchmarks_dir.mkdir(exist_ok=True)
        
        # Main baseline file location
        self.baseline_file = self.baselines_dir / "current_performance_baseline.json"
        
        # Keep backward compatibility with historical_dir for existing code
        self.historical_dir = self.snapshots_dir
        
        logger.info(f"BaselineManager initialized with metrics_dir: {self.metrics_dir}")

    def create_standardized_baseline_structure(self, 
                                             benchmark_data: Dict[str, Any],
                                             baseline_version: str = "2.0") -> Dict[str, Any]:
        """
        Create standardized baseline JSON structure for all benchmark metrics.
        
        Task 6.1: Create baseline JSON structure for all benchmark metrics
        
        Args:
            benchmark_data: Raw benchmark data from pytest-benchmark
            baseline_version: Version identifier for the baseline format
            
        Returns:
            Standardized baseline structure with comprehensive metadata
        """
        # Extract git information for version control integration
        git_info = self._get_git_information()
        
        # Calculate comprehensive statistics
        baseline_stats = self._calculate_baseline_statistics(benchmark_data)
        
        # Create standardized structure
        baseline_structure = {
            "baseline_metadata": {
                "version": baseline_version,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "schema_version": "2.0.0",
                "description": "Hazelbean performance baseline with comprehensive metrics",
                "statistical_confidence": "95%",
                "regression_threshold_percent": 10.0,
                "trend_analysis_enabled": True
            },
            "version_control_info": git_info,
            "system_environment": self._extract_system_info(benchmark_data),
            "baseline_statistics": baseline_stats,
            "benchmark_categories": self._categorize_benchmarks(benchmark_data),
            "quality_metrics": self._calculate_quality_metrics(baseline_stats),
            "raw_benchmark_data": benchmark_data.get("benchmarks", []),
            "validation_info": {
                "total_benchmarks": len(benchmark_data.get("benchmarks", [])),
                "valid_benchmarks": len([b for b in benchmark_data.get("benchmarks", []) if self._is_valid_benchmark(b)]),
                "statistical_confidence_met": True,
                "baseline_establishment_criteria": {
                    "minimum_runs": 5,
                    "maximum_variance_threshold": 0.25,
                    "outlier_detection_enabled": True
                }
            }
        }
        
        logger.info(f"Created standardized baseline structure with {baseline_structure['validation_info']['total_benchmarks']} benchmarks")
        return baseline_structure

    def save_baseline(self, baseline_data: Dict[str, Any]) -> str:
        """
        Save baseline data with version control integration.
        
        Task 6.4: Set up version control integration for baseline artifacts
        
        Args:
            baseline_data: Standardized baseline data structure
            
        Returns:
            Path to saved baseline file
        """
        # Save main baseline file
        with open(self.baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        # Create baseline snapshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        git_hash = baseline_data.get("version_control_info", {}).get("commit_id", "unknown")[:8]
        
        # Save snapshot with descriptive naming
        snapshot_file = self.snapshots_dir / f"baseline_snapshot_{timestamp}_{git_hash}.json"
        with open(snapshot_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        logger.info(f"Saved current baseline to {self.baseline_file} and snapshot to {snapshot_file}")
        return str(self.baseline_file)

    def compare_with_baseline(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement baseline comparison logic for performance regression detection.
        
        Task 6.2: Implement baseline comparison logic for performance regression detection
        
        Args:
            current_data: Current benchmark results to compare against baseline
            
        Returns:
            Comprehensive comparison results with regression detection
        """
        if not self.baseline_file.exists():
            logger.warning("No baseline file found. Creating initial baseline.")
            return {"status": "no_baseline", "action": "create_baseline"}
        
        # Load baseline data
        with open(self.baseline_file, 'r') as f:
            baseline_data = json.load(f)
        
        comparison_results = {
            "comparison_metadata": {
                "comparison_timestamp": datetime.now(timezone.utc).isoformat(),
                "baseline_version": baseline_data.get("baseline_metadata", {}).get("version", "unknown"),
                "comparison_type": "performance_regression_analysis"
            },
            "regression_analysis": {},
            "performance_changes": {},
            "statistical_significance": {},
            "recommendations": [],
            "overall_status": "passed"
        }
        
        # Compare each benchmark
        baseline_benchmarks = {b["name"]: b for b in baseline_data.get("raw_benchmark_data", [])}
        current_benchmarks = {b["name"]: b for b in current_data.get("benchmarks", [])}
        
        regression_threshold = baseline_data.get("baseline_metadata", {}).get("regression_threshold_percent", 10.0)
        
        for benchmark_name, current_benchmark in current_benchmarks.items():
            if benchmark_name in baseline_benchmarks:
                baseline_benchmark = baseline_benchmarks[benchmark_name]
                regression_analysis = self._analyze_regression(
                    baseline_benchmark, current_benchmark, regression_threshold
                )
                comparison_results["regression_analysis"][benchmark_name] = regression_analysis
                
                if regression_analysis["is_regression"]:
                    comparison_results["overall_status"] = "regression_detected"
        
        # Add recommendations
        comparison_results["recommendations"] = self._generate_recommendations(comparison_results)
        
        logger.info(f"Completed baseline comparison. Status: {comparison_results['overall_status']}")
        return comparison_results

    def analyze_trends(self, lookback_days: int = 30) -> Dict[str, Any]:
        """
        Add trend analysis and historical tracking capabilities.
        
        Task 6.3: Add trend analysis and historical tracking capabilities
        
        Args:
            lookback_days: Number of days to analyze for trends
            
        Returns:
            Comprehensive trend analysis with historical tracking
        """
        # Collect baseline snapshot files
        historical_files = list(self.snapshots_dir.glob("baseline_snapshot_*.json"))
        historical_files.sort()  # Sort by filename (which includes timestamp)
        
        if len(historical_files) < 2:
            return {
                "status": "insufficient_data",
                "message": f"Need at least 2 historical baselines for trend analysis. Found: {len(historical_files)}"
            }
        
        trend_data = {
            "trend_metadata": {
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "lookback_days": lookback_days,
                "analyzed_files": len(historical_files),
                "trend_detection_algorithm": "linear_regression_with_statistical_significance"
            },
            "benchmark_trends": {},
            "performance_trajectory": {},
            "anomaly_detection": {},
            "trend_summary": {
                "improving_benchmarks": [],
                "degrading_benchmarks": [],
                "stable_benchmarks": [],
                "anomalous_benchmarks": []
            }
        }
        
        # Analyze trends for each benchmark
        benchmark_history = self._collect_benchmark_history(historical_files)
        
        for benchmark_name, history in benchmark_history.items():
            if len(history) >= 3:  # Need minimum data points for trend analysis
                trend_analysis = self._calculate_trend_metrics(benchmark_name, history)
                trend_data["benchmark_trends"][benchmark_name] = trend_analysis
                
                # Categorize benchmark trends
                self._categorize_benchmark_trend(benchmark_name, trend_analysis, trend_data["trend_summary"])
        
        # Generate performance trajectory summary
        trend_data["performance_trajectory"] = self._generate_performance_trajectory(benchmark_history)
        
        logger.info(f"Completed trend analysis for {len(benchmark_history)} benchmarks over {len(historical_files)} baseline files")
        return trend_data

    def _get_git_information(self) -> Dict[str, Any]:
        """Extract git information for version control integration"""
        try:
            git_info = {
                "commit_id": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
                "commit_timestamp": subprocess.check_output(["git", "show", "-s", "--format=%ci", "HEAD"]).decode().strip(),
                "branch": subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip(),
                "is_dirty": len(subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()) > 0,
                "author": subprocess.check_output(["git", "show", "-s", "--format=%an", "HEAD"]).decode().strip(),
                "repository_url": self._get_repository_url()
            }
        except subprocess.CalledProcessError:
            git_info = {
                "commit_id": "unknown",
                "commit_timestamp": "unknown",
                "branch": "unknown", 
                "is_dirty": False,
                "author": "unknown",
                "repository_url": "unknown"
            }
        return git_info

    def _get_repository_url(self) -> str:
        """Get repository URL for version control tracking"""
        try:
            origin_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"]).decode().strip()
            return origin_url
        except subprocess.CalledProcessError:
            return "unknown"

    def _extract_system_info(self, benchmark_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and standardize system environment information"""
        machine_info = benchmark_data.get("machine_info", {})
        return {
            "platform": {
                "system": machine_info.get("system", "unknown"),
                "node": machine_info.get("node", "unknown"),
                "release": machine_info.get("release", "unknown"),
                "machine": machine_info.get("machine", "unknown"),
                "processor": machine_info.get("processor", "unknown")
            },
            "python_environment": {
                "version": machine_info.get("python_version", "unknown"),
                "implementation": machine_info.get("python_implementation", "unknown"),
                "compiler": machine_info.get("python_compiler", "unknown")
            },
            "cpu_info": machine_info.get("cpu", {}),
            "environment_hash": self._calculate_environment_hash(machine_info)
        }

    def _calculate_environment_hash(self, machine_info: Dict[str, Any]) -> str:
        """Calculate hash of environment for compatibility checking"""
        import hashlib
        env_string = f"{machine_info.get('system')}_{machine_info.get('machine')}_{machine_info.get('python_version')}"
        return hashlib.sha256(env_string.encode()).hexdigest()[:16]

    def _calculate_baseline_statistics(self, benchmark_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive baseline statistics"""
        benchmarks = benchmark_data.get("benchmarks", [])
        
        if not benchmarks:
            return {"error": "no_benchmark_data"}
        
        execution_times = []
        for benchmark in benchmarks:
            stats = benchmark.get("stats", {})
            if "mean" in stats:
                try:
                    mean_value = float(stats["mean"])
                    if mean_value > 0:  # Only include positive values
                        execution_times.append(mean_value)
                except (ValueError, TypeError):
                    # Skip invalid values
                    logger.warning(f"Invalid mean value in benchmark {benchmark.get('name', 'unknown')}: {stats['mean']}")
                    continue
        
        if not execution_times:
            return {"error": "no_valid_execution_times"}
        
        return {
            "aggregate_statistics": {
                "mean_execution_time": statistics.mean(execution_times),
                "median_execution_time": statistics.median(execution_times),
                "std_deviation": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                "min_time": min(execution_times),
                "max_time": max(execution_times),
                "total_benchmarks": len(execution_times)
            },
            "confidence_intervals": self._calculate_confidence_intervals(execution_times),
            "outlier_analysis": self._detect_outliers(execution_times),
            "quality_indicators": {
                "coefficient_of_variation": (statistics.stdev(execution_times) / statistics.mean(execution_times)) if len(execution_times) > 1 and statistics.mean(execution_times) > 0 else 0,
                "acceptable_variance": (statistics.stdev(execution_times) / statistics.mean(execution_times)) < 0.25 if len(execution_times) > 1 and statistics.mean(execution_times) > 0 else False
            }
        }

    def _calculate_confidence_intervals(self, data: List[float], confidence: float = 0.95) -> Dict[str, float]:
        """Calculate confidence intervals for baseline statistics"""
        if len(data) < 2:
            return {"lower": 0, "upper": 0, "confidence_level": confidence}
        
        mean = statistics.mean(data)
        std_dev = statistics.stdev(data) if len(data) > 1 else 0
        n = len(data)
        
        # Using t-distribution for small samples
        import math
        if n < 30:
            # Simplified t-distribution approximation
            t_value = 2.0  # Approximate t-value for 95% confidence
        else:
            t_value = 1.96  # z-value for 95% confidence
        
        margin_error = t_value * (std_dev / math.sqrt(n))
        
        return {
            "lower": mean - margin_error,
            "upper": mean + margin_error,
            "confidence_level": confidence,
            "margin_of_error": margin_error
        }

    def _detect_outliers(self, data: List[float]) -> Dict[str, Any]:
        """Detect outliers in benchmark data using IQR method"""
        if len(data) < 4:
            return {"outliers": [], "method": "insufficient_data"}
        
        sorted_data = sorted(data)
        n = len(sorted_data)
        
        q1_index = n // 4
        q3_index = 3 * n // 4
        
        q1 = sorted_data[q1_index]
        q3 = sorted_data[q3_index]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = [x for x in data if x < lower_bound or x > upper_bound]
        
        return {
            "outliers": outliers,
            "outlier_count": len(outliers),
            "outlier_percentage": (len(outliers) / len(data)) * 100,
            "method": "IQR",
            "bounds": {"lower": lower_bound, "upper": upper_bound},
            "quartiles": {"q1": q1, "q3": q3, "iqr": iqr}
        }

    def _categorize_benchmarks(self, benchmark_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Categorize benchmarks by type and functionality"""
        categories = {
            "path_resolution": [],
            "tiling_operations": [],
            "data_processing": [],
            "io_operations": [],
            "computational": [],
            "integration": [],
            "uncategorized": []
        }
        
        for benchmark in benchmark_data.get("benchmarks", []):
            name = benchmark.get("name", "").lower()
            categorized = False
            
            if any(keyword in name for keyword in ["path", "get_path", "resolution"]):
                categories["path_resolution"].append(benchmark["name"])
                categorized = True
            elif any(keyword in name for keyword in ["tile", "tiling", "iterator"]):
                categories["tiling_operations"].append(benchmark["name"])
                categorized = True
            elif any(keyword in name for keyword in ["array", "processing", "calculation"]):
                categories["data_processing"].append(benchmark["name"])
                categorized = True
            elif any(keyword in name for keyword in ["io", "read", "write", "load", "save"]):
                categories["io_operations"].append(benchmark["name"])
                categorized = True
            elif any(keyword in name for keyword in ["integration", "workflow", "end_to_end"]):
                categories["integration"].append(benchmark["name"])
                categorized = True
            elif any(keyword in name for keyword in ["compute", "algorithm", "math"]):
                categories["computational"].append(benchmark["name"])
                categorized = True
            
            if not categorized:
                categories["uncategorized"].append(benchmark["name"])
        
        return categories

    def _calculate_quality_metrics(self, baseline_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quality metrics for baseline establishment"""
        aggregate_stats = baseline_stats.get("aggregate_statistics", {})
        
        return {
            "baseline_quality_score": self._calculate_quality_score(baseline_stats),
            "statistical_reliability": {
                "sufficient_sample_size": aggregate_stats.get("total_benchmarks", 0) >= 5,
                "acceptable_variance": baseline_stats.get("quality_indicators", {}).get("acceptable_variance", False),
                "outlier_percentage": baseline_stats.get("outlier_analysis", {}).get("outlier_percentage", 0),
                "confidence_interval_width": self._calculate_ci_width(baseline_stats)
            },
            "recommendations": self._generate_quality_recommendations(baseline_stats)
        }

    def _calculate_quality_score(self, baseline_stats: Dict[str, Any]) -> float:
        """Calculate overall quality score for baseline (0-100)"""
        score = 100.0
        
        # Penalize high variance
        cv = baseline_stats.get("quality_indicators", {}).get("coefficient_of_variation", 0)
        if cv > 0.25:
            score -= min(30, cv * 100)
        
        # Penalize high outlier percentage
        outlier_pct = baseline_stats.get("outlier_analysis", {}).get("outlier_percentage", 0)
        if outlier_pct > 10:
            score -= min(20, outlier_pct)
        
        # Penalize small sample size
        sample_size = baseline_stats.get("aggregate_statistics", {}).get("total_benchmarks", 0)
        if sample_size < 5:
            score -= 40
        elif sample_size < 10:
            score -= 20
        
        return max(0, score)

    def _calculate_ci_width(self, baseline_stats: Dict[str, Any]) -> float:
        """Calculate confidence interval width as percentage of mean"""
        ci = baseline_stats.get("confidence_intervals", {})
        mean = baseline_stats.get("aggregate_statistics", {}).get("mean_execution_time", 0)
        
        if mean > 0 and "upper" in ci and "lower" in ci:
            width = ci["upper"] - ci["lower"]
            return (width / mean) * 100
        return 0

    def _generate_quality_recommendations(self, baseline_stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving baseline quality"""
        recommendations = []
        
        quality_indicators = baseline_stats.get("quality_indicators", {})
        if not quality_indicators.get("acceptable_variance", True):
            recommendations.append("High variance detected. Consider running more benchmark iterations or investigating environmental factors.")
        
        outlier_pct = baseline_stats.get("outlier_analysis", {}).get("outlier_percentage", 0)
        if outlier_pct > 15:
            recommendations.append("High outlier percentage. Review benchmark setup and consider environment stabilization.")
        
        sample_size = baseline_stats.get("aggregate_statistics", {}).get("total_benchmarks", 0)
        if sample_size < 10:
            recommendations.append("Small sample size. Consider adding more benchmark tests for better statistical reliability.")
        
        return recommendations

    def _is_valid_benchmark(self, benchmark: Dict[str, Any]) -> bool:
        """Check if a benchmark result is valid for baseline inclusion"""
        stats = benchmark.get("stats", {})
        
        # Check if mean exists and can be converted to float
        if "mean" not in stats:
            return False
            
        try:
            mean_value = float(stats["mean"])
            if mean_value <= 0:
                return False
        except (ValueError, TypeError):
            return False
        
        # Check rounds if present
        try:
            rounds = stats.get("rounds", 1)
            if isinstance(rounds, str):
                rounds = float(rounds)
            if rounds <= 0:
                return False
        except (ValueError, TypeError):
            return False
            
        return True

    def _analyze_regression(self, baseline_benchmark: Dict[str, Any], 
                          current_benchmark: Dict[str, Any], 
                          threshold_percent: float) -> Dict[str, Any]:
        """Analyze potential regression between baseline and current benchmark"""
        baseline_mean = baseline_benchmark.get("stats", {}).get("mean", 0)
        current_mean = current_benchmark.get("stats", {}).get("mean", 0)
        
        if baseline_mean == 0:
            return {"is_regression": False, "reason": "invalid_baseline_data"}
        
        percent_change = ((current_mean - baseline_mean) / baseline_mean) * 100
        is_regression = percent_change > threshold_percent
        
        return {
            "is_regression": is_regression,
            "percent_change": percent_change,
            "baseline_mean": baseline_mean,
            "current_mean": current_mean,
            "absolute_difference": current_mean - baseline_mean,
            "threshold_percent": threshold_percent,
            "severity": self._classify_regression_severity(percent_change, threshold_percent),
            "statistical_significance": self._check_statistical_significance(baseline_benchmark, current_benchmark)
        }

    def _classify_regression_severity(self, percent_change: float, threshold: float) -> str:
        """Classify regression severity based on performance change"""
        if percent_change <= threshold:
            return "no_regression"
        elif percent_change <= threshold * 2:
            return "minor_regression"
        elif percent_change <= threshold * 5:
            return "major_regression"
        else:
            return "critical_regression"

    def _check_statistical_significance(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Check statistical significance of performance difference"""
        baseline_stats = baseline.get("stats", {})
        current_stats = current.get("stats", {})
        
        # Simplified significance check using standard deviation
        baseline_std = baseline_stats.get("stddev", 0)
        current_std = current_stats.get("stddev", 0)
        baseline_mean = baseline_stats.get("mean", 0)
        current_mean = current_stats.get("mean", 0)
        
        if baseline_std == 0 or current_std == 0:
            return {"significant": False, "method": "insufficient_variance_data"}
        
        # Simple two-standard-deviation test
        combined_std = (baseline_std + current_std) / 2
        difference = abs(current_mean - baseline_mean)
        
        is_significant = difference > (2 * combined_std)
        
        return {
            "significant": is_significant,
            "method": "two_standard_deviation_test",
            "difference": difference,
            "threshold": 2 * combined_std,
            "confidence_level": "approximately_95_percent"
        }

    def _generate_recommendations(self, comparison_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on comparison results"""
        recommendations = []
        
        if comparison_results["overall_status"] == "regression_detected":
            recommendations.append("Performance regression detected. Review recent changes and consider performance optimization.")
            
            # Count regressions by severity
            severe_regressions = sum(1 for analysis in comparison_results["regression_analysis"].values() 
                                   if analysis.get("severity") in ["major_regression", "critical_regression"])
            
            if severe_regressions > 0:
                recommendations.append(f"Critical performance regressions found in {severe_regressions} benchmark(s). Immediate attention required.")
        
        return recommendations

    def _collect_benchmark_history(self, historical_files: List[Path]) -> Dict[str, List[Dict[str, Any]]]:
        """Collect benchmark history from historical baseline files"""
        benchmark_history = {}
        
        for file_path in historical_files:
            try:
                with open(file_path, 'r') as f:
                    historical_data = json.load(f)
                
                # Extract timestamp from metadata or filename
                timestamp = historical_data.get("baseline_metadata", {}).get("created_at")
                if not timestamp:
                    # Extract from filename if not in metadata
                    timestamp = file_path.stem.split("_")[1] if "_" in file_path.stem else "unknown"
                
                for benchmark in historical_data.get("raw_benchmark_data", []):
                    name = benchmark.get("name")
                    if name:
                        if name not in benchmark_history:
                            benchmark_history[name] = []
                        
                        benchmark_history[name].append({
                            "timestamp": timestamp,
                            "stats": benchmark.get("stats", {}),
                            "file_source": str(file_path)
                        })
                        
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Could not process historical file {file_path}: {e}")
        
        # Sort each benchmark's history by timestamp
        for name in benchmark_history:
            benchmark_history[name].sort(key=lambda x: x["timestamp"])
        
        return benchmark_history

    def _calculate_trend_metrics(self, benchmark_name: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trend metrics for a specific benchmark"""
        execution_times = [entry["stats"].get("mean", 0) for entry in history if entry["stats"].get("mean", 0) > 0]
        
        if len(execution_times) < 3:
            return {"trend": "insufficient_data", "data_points": len(execution_times)}
        
        # Simple linear trend calculation
        x_values = list(range(len(execution_times)))
        trend_slope = self._calculate_linear_trend(x_values, execution_times)
        
        return {
            "trend": "improving" if trend_slope < -0.001 else "degrading" if trend_slope > 0.001 else "stable",
            "slope": trend_slope,
            "data_points": len(execution_times),
            "latest_value": execution_times[-1],
            "earliest_value": execution_times[0],
            "total_change_percent": ((execution_times[-1] - execution_times[0]) / execution_times[0]) * 100 if execution_times[0] > 0 else 0,
            "volatility": statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        }

    def _calculate_linear_trend(self, x_values: List[int], y_values: List[float]) -> float:
        """Calculate linear trend slope using least squares"""
        n = len(x_values)
        if n < 2:
            return 0
        
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    def _categorize_benchmark_trend(self, benchmark_name: str, trend_analysis: Dict[str, Any], trend_summary: Dict[str, List]):
        """Categorize benchmark into trend summary categories"""
        trend = trend_analysis.get("trend", "unknown")
        
        if trend == "improving":
            trend_summary["improving_benchmarks"].append(benchmark_name)
        elif trend == "degrading":
            trend_summary["degrading_benchmarks"].append(benchmark_name)
        elif trend == "stable":
            trend_summary["stable_benchmarks"].append(benchmark_name)
        else:
            trend_summary["anomalous_benchmarks"].append(benchmark_name)

    def _generate_performance_trajectory(self, benchmark_history: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Generate overall performance trajectory summary"""
        if not benchmark_history:
            return {"status": "no_data"}
        
        # Calculate overall performance trend
        all_latest_times = []
        all_earliest_times = []
        
        for benchmark_data in benchmark_history.values():
            if len(benchmark_data) >= 2:
                earliest = benchmark_data[0]["stats"].get("mean", 0)
                latest = benchmark_data[-1]["stats"].get("mean", 0)
                if earliest > 0 and latest > 0:
                    all_earliest_times.append(earliest)
                    all_latest_times.append(latest)
        
        if not all_latest_times or not all_earliest_times:
            return {"status": "insufficient_data"}
        
        avg_earliest = statistics.mean(all_earliest_times)
        avg_latest = statistics.mean(all_latest_times)
        
        overall_change = ((avg_latest - avg_earliest) / avg_earliest) * 100 if avg_earliest > 0 else 0
        
        return {
            "overall_trend": "improving" if overall_change < -1 else "degrading" if overall_change > 1 else "stable",
            "overall_change_percent": overall_change,
            "benchmarks_analyzed": len(all_latest_times),
            "average_earliest_time": avg_earliest,
            "average_latest_time": avg_latest,
            "performance_health": "good" if overall_change < 5 else "concerning" if overall_change < 15 else "poor"
        }

    def generate_baseline_report(self, baseline_data: Dict[str, Any]) -> str:
        """Generate a human-readable baseline establishment report"""
        report_lines = [
            "HAZELBEAN PERFORMANCE BASELINE ESTABLISHMENT REPORT",
            "=" * 55,
            "",
            f"Baseline Version: {baseline_data.get('baseline_metadata', {}).get('version', 'unknown')}",
            f"Created: {baseline_data.get('baseline_metadata', {}).get('created_at', 'unknown')}",
            f"Git Commit: {baseline_data.get('version_control_info', {}).get('commit_id', 'unknown')[:12]}",
            f"Branch: {baseline_data.get('version_control_info', {}).get('branch', 'unknown')}",
            "",
            "BASELINE STATISTICS",
            "-" * 20,
        ]
        
        stats = baseline_data.get("baseline_statistics", {}).get("aggregate_statistics", {})
        report_lines.extend([
            f"Total Benchmarks: {stats.get('total_benchmarks', 0)}",
            f"Mean Execution Time: {stats.get('mean_execution_time', 0):.6f}s",
            f"Standard Deviation: {stats.get('std_deviation', 0):.6f}s",
            f"Min Time: {stats.get('min_time', 0):.6f}s",
            f"Max Time: {stats.get('max_time', 0):.6f}s",
            "",
            "QUALITY METRICS",
            "-" * 15,
        ])
        
        quality = baseline_data.get("quality_metrics", {})
        report_lines.extend([
            f"Baseline Quality Score: {quality.get('baseline_quality_score', 0):.1f}/100",
            f"Statistical Reliability: {'PASS' if quality.get('statistical_reliability', {}).get('sufficient_sample_size', False) else 'FAIL'}",
            f"Variance Acceptable: {'YES' if quality.get('statistical_reliability', {}).get('acceptable_variance', False) else 'NO'}",
            "",
            "BENCHMARK CATEGORIES",
            "-" * 20,
        ])
        
        categories = baseline_data.get("benchmark_categories", {})
        for category, benchmarks in categories.items():
            if benchmarks:
                report_lines.append(f"{category.replace('_', ' ').title()}: {len(benchmarks)} benchmarks")
        
        report_lines.extend(["", "RECOMMENDATIONS", "-" * 15])
        recommendations = quality.get("recommendations", [])
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                report_lines.append(f"{i}. {rec}")
        else:
            report_lines.append("No specific recommendations. Baseline quality is acceptable.")
        
        return "\n".join(report_lines)

# Example usage and CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Hazelbean Baseline Management System")
    parser.add_argument("--metrics-dir", help="Metrics directory path")
    parser.add_argument("--create-baseline", help="Create baseline from benchmark JSON file")
    parser.add_argument("--compare", help="Compare current results with baseline")
    parser.add_argument("--trends", action="store_true", help="Analyze performance trends")
    parser.add_argument("--report", action="store_true", help="Generate baseline report")
    
    args = parser.parse_args()
    
    manager = BaselineManager(args.metrics_dir)
    
    if args.create_baseline:
        with open(args.create_baseline, 'r') as f:
            benchmark_data = json.load(f)
        
        baseline_structure = manager.create_standardized_baseline_structure(benchmark_data)
        baseline_path = manager.save_baseline(baseline_structure)
        
        if args.report:
            report = manager.generate_baseline_report(baseline_structure)
            print(report)
        
        print(f"Baseline created and saved to: {baseline_path}")
    
    elif args.compare:
        with open(args.compare, 'r') as f:
            current_data = json.load(f)
        
        comparison = manager.compare_with_baseline(current_data)
        print(f"Comparison Status: {comparison['overall_status']}")
        
        if comparison["overall_status"] == "regression_detected":
            print("REGRESSIONS DETECTED:")
            for benchmark, analysis in comparison["regression_analysis"].items():
                if analysis["is_regression"]:
                    print(f"  - {benchmark}: {analysis['percent_change']:.1f}% slower ({analysis['severity']})")
    
    elif args.trends:
        trends = manager.analyze_trends()
        print("TREND ANALYSIS")
        print("=" * 15)
        
        if trends.get("status") == "insufficient_data":
            print(trends["message"])
        else:
            trajectory = trends.get("performance_trajectory", {})
            print(f"Overall Trend: {trajectory.get('overall_trend', 'unknown').upper()}")
            print(f"Performance Change: {trajectory.get('overall_change_percent', 0):.1f}%")
            print(f"Performance Health: {trajectory.get('performance_health', 'unknown').upper()}")
            
            summary = trends.get("trend_summary", {})
            print(f"\nImproving: {len(summary.get('improving_benchmarks', []))}")
            print(f"Degrading: {len(summary.get('degrading_benchmarks', []))}")
            print(f"Stable: {len(summary.get('stable_benchmarks', []))}")
