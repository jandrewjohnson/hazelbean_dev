#!/usr/bin/env python3
"""
Create an HTML dashboard for benchmark visualization
"""

import json
import os
import sys
import threading
import webbrowser
import socketserver
import http.server
import socket
from pathlib import Path

def find_free_port(start_port=8080):
    """Find an available port starting from start_port"""
    port = start_port
    while port < start_port + 10:  # Try 10 ports
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            port += 1
    return None


def start_local_server(port=8080, directory="."):
    """Start a simple HTTP server in a separate thread"""
    os.chdir(directory)
    
    class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            # Suppress log messages
            pass
    
    try:
        with socketserver.TCPServer(("localhost", port), QuietHTTPRequestHandler) as httpd:
            print(f"🌐 Starting local server at http://localhost:{port}")
            print(f"📊 Dashboard URL: http://localhost:{port}/benchmark_dashboard.html")
            print(f"⏹️  Press Ctrl+C to stop the server")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")


def create_html_dashboard(json_file, output_html="benchmark_dashboard.html", start_server=True):
    """Create an interactive HTML dashboard"""
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    if 'benchmarks' not in data:
        print("No benchmark data found")
        return
    
    # Extract data for charts
    benchmarks = data['benchmarks']
    names = [b['name'] for b in benchmarks]
    mean_times = [b['stats']['mean'] * 1000 for b in benchmarks]  # Convert to ms
    
    # Calculate performance classifications
    fastest_time = min(mean_times)
    slowest_time = max(mean_times)
    average_time = sum(mean_times) / len(mean_times)
    
    # Get system info for context
    system_info = data.get('machine_info', {})
    commit_info = data.get('commit_info', {})
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Hazelbean Performance Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               margin: 0; padding: 40px; background: #f8f9fa; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; 
                     padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; }}
        h3 {{ color: #2980b9; }}
        .chart {{ 
            margin: 30px 0; 
            min-height: 400px;
            width: 100%;
            overflow: visible;
        }}
        .stats {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                 color: white; padding: 25px; border-radius: 12px; margin: 20px 0; }}
        .stats h2 {{ 
            color: #FFE4B5; 
            font-size: 1.8em;
            margin: 0 0 20px 0;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            border-bottom: 2px solid rgba(255, 228, 181, 0.3);
            padding-bottom: 10px;
            font-weight: 600;
        }}
        .summary-column {{ 
            background: rgba(255, 255, 255, 0.1); 
            padding: 20px; 
            border-radius: 8px; 
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-bottom: 3px solid rgba(255, 255, 255, 0.4);
            backdrop-filter: blur(10px);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .summary-column:hover {{ 
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            border-bottom: 3px solid #ffffff;
        }}
        .summary-value {{ 
            font-weight: bold; 
            color: #ffffff; 
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
        }}
        .explanation {{ background: #e8f4fd; padding: 20px; border-radius: 10px; 
                       border-left: 4px solid #3498db; margin: 20px 0; }}
        .warning {{ background: #fff3cd; padding: 15px; border-radius: 10px; 
                   border-left: 4px solid #ffc107; margin: 15px 0; }}
        .success {{ background: #d4edda; padding: 15px; border-radius: 10px; 
                   border-left: 4px solid #28a745; margin: 15px 0; }}
        .danger {{ background: #f8d7da; padding: 15px; border-radius: 10px; 
                  border-left: 4px solid #dc3545; margin: 15px 0; }}
        .performance-guide {{ background: #f8f9fa; padding: 20px; border-radius: 10px; 
                             border: 1px solid #dee2e6; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; 
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        th {{ background: #f8f9fa; padding: 12px; text-align: left; 
             border-bottom: 2px solid #dee2e6; font-weight: 600; }}
        td {{ padding: 12px; border-bottom: 1px solid #dee2e6; }}
        tr:hover {{ background: #f5f5f5; }}
        .benchmark-name {{ font-family: 'Courier New', monospace; 
                          background: #f8f9fa; font-weight: bold; }}
        th {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
             color: white; padding: 15px; text-align: left; }}
        td {{ border: 1px solid #ddd; padding: 12px; }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        .benchmark-name {{ font-weight: bold; color: #2c3e50; }}
        .system-info {{ background: #e9ecef; padding: 15px; border-radius: 10px; 
                       font-family: 'Monaco', 'Consolas', monospace; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>&#128640; Hazelbean Performance Dashboard</h1>
        
        <div class="explanation">
            <h3>📖 What Am I Looking At?</h3>
            <p><strong>This dashboard shows the performance of different Hazelbean operations.</strong> 
            Each benchmark measures how fast specific functions execute, helping identify optimization opportunities 
            and detect performance regressions over time.</p>
            
            <p><strong>Key Metrics Explained:</strong></p>
            <ul>
                <li><strong>Mean Time:</strong> Average execution time across multiple test runs</li>
                <li><strong>Min/Max Time:</strong> Fastest and slowest individual execution</li>
                <li><strong>Rounds:</strong> Number of times the test was executed for statistical accuracy</li>
            </ul>
        </div>
    
        <div class="stats">
            <h2>📈 Performance Summary</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px;">
                <div class="summary-column">
                    <h4 style="margin: 0 0 10px 0; font-size: 0.9em; opacity: 0.9;">&#128202; Total Benchmarks</h4>
                    <p class="summary-value" style="font-size: 2.2em; margin: 0; line-height: 1;">{len(benchmarks)}</p>
                </div>
                <div class="summary-column">
                    <h4 style="margin: 0 0 10px 0; font-size: 0.9em; opacity: 0.9;">&#128640; Fastest Operation</h4>
                    <p class="summary-value" style="margin: 0; font-size: 0.85em; line-height: 1.2;">{min(names, key=lambda x: next(b['stats']['mean'] for b in benchmarks if b['name'] == x))}</p>
                    <p class="summary-value" style="margin: 5px 0 0 0; font-size: 1.3em; color: #90EE90;">{min(mean_times):.3f}ms</p>
                </div>
                <div class="summary-column">
                    <h4 style="margin: 0 0 10px 0; font-size: 0.9em; opacity: 0.9;">&#128012; Slowest Operation</h4>
                    <p class="summary-value" style="margin: 0; font-size: 0.85em; line-height: 1.2;">{max(names, key=lambda x: next(b['stats']['mean'] for b in benchmarks if b['name'] == x))}</p>
                    <p class="summary-value" style="margin: 5px 0 0 0; font-size: 1.3em; color: #FFB6C1;">{max(mean_times):.3f}ms</p>
                </div>
                <div class="summary-column">
                    <h4 style="margin: 0 0 10px 0; font-size: 0.9em; opacity: 0.9;">&#128202; Average Time</h4>
                    <p class="summary-value" style="margin: 0; font-size: 1.8em; line-height: 1; color: #87CEEB;">{average_time:.3f}ms</p>
                </div>
            </div>
        </div>
        
        <div class="performance-guide">
            <h3>&#127919; How to Interpret Performance Results</h3>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
                <div class="success">
                    <h4>&#128640; Excellent Performance (&lt; 1ms)</h4>
                    <p>These operations are highly optimized and run very quickly. No action needed.</p>
                </div>
                <div class="warning">
                    <h4>&#9888; Moderate Performance (1ms - 100ms)</h4>
                    <p>Acceptable performance for most use cases. Consider optimization if used frequently.</p>
                </div>
                <div class="danger">
                    <h4>&#128012; Slow Performance (&gt; 100ms)</h4>
                    <p>May impact user experience. Consider optimization or algorithm improvements.</p>
                </div>
            </div>
            
            <h4>&#128269; What Does It Mean When a Benchmark Takes Longer?</h4>
            <ul>
                <li><strong>Higher complexity:</strong> The operation processes more data or performs more calculations</li>
                <li><strong>I/O operations:</strong> File reading/writing operations are typically slower than in-memory computations</li>
                <li><strong>System resources:</strong> CPU load, memory usage, or disk speed can affect performance</li>
                <li><strong>Algorithm efficiency:</strong> Some algorithms are inherently faster than others for the same task</li>
                <li><strong>Optimization opportunity:</strong> Slower benchmarks may benefit from code optimization</li>
            </ul>
            
            <h4>&#127919; What Should I Do About Slow Benchmarks?</h4>
            <ul>
                <li><strong>Prioritize by usage:</strong> Focus on optimizing frequently-used slow operations first</li>
                <li><strong>Profile the code:</strong> Use profiling tools to identify bottlenecks within slow functions</li>
                <li><strong>Consider caching:</strong> Cache results of expensive operations when possible</li>
                <li><strong>Optimize algorithms:</strong> Look for more efficient algorithms or data structures</li>
                <li><strong>Monitor trends:</strong> Track performance over time to catch regressions early</li>
            </ul>
        </div>
        
        <div class="system-info">
            <h3>&#128187; Test Environment</h3>
            <p><strong>System:</strong> {system_info.get('system', 'Unknown')} {system_info.get('release', '')}</p>
            <p><strong>CPU:</strong> {system_info.get('cpu', {}).get('brand_raw', 'Unknown')} ({system_info.get('cpu', {}).get('count', 'Unknown')} cores)</p>
            <p><strong>Python:</strong> {system_info.get('python_version', 'Unknown')}</p>
            <p><strong>Git Branch:</strong> {commit_info.get('branch', 'Unknown')} (Commit: {commit_info.get('id', 'Unknown')[:8]}...)</p>
        </div>
    
        <div class="explanation">
            <p><strong>&#128221; About These Benchmarks:</strong> These performance metrics are generated from 
            <strong>pytest-benchmark tests</strong> that measure actual Hazelbean operations including 
            array processing, file I/O, and path resolution functionality.</p>
        </div>
        
        <h2>&#128202; Performance Visualization</h2>
        <!-- Full width charts stacked vertically -->
        <div id="bar-chart" class="chart" style="height: 500px; margin: 30px 0;"></div>
        <div id="pie-chart" class="chart" style="height: 500px; margin: 30px 0;"></div>
        <div id="performance-distribution" class="chart" style="height: 600px; margin: 30px 0;"></div>
    
        <div id="detailed-table" class="chart"></div>
    
    <script>
        // Bar chart
        var trace1 = {{
            x: {names},
            y: {mean_times},
            type: 'bar',
            marker: {{
                color: ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
            }}
        }};
        
        var layout1 = {{
            title: 'Benchmark Execution Times',
            xaxis: {{ 
                title: 'Benchmark Name',
                tickangle: -45,
                automargin: true
            }},
            yaxis: {{ title: 'Mean Time (ms)' }},
            height: 500,
            margin: {{
                l: 60,
                r: 30,
                t: 60,
                b: 120
            }}
        }};
        
        Plotly.newPlot('bar-chart', [trace1], layout1);
        
        // Performance distribution pie chart
        var performanceCategories = [];
        var performanceCounts = [0, 0, 0]; // Excellent, Moderate, Slow
        var categoryColors = ['#28a745', '#ffc107', '#dc3545'];
        
        benchmarks.forEach(function(benchmark) {{
            var meanTimeMs = benchmark.stats.mean * 1000;
            if (meanTimeMs < 1) {{
                performanceCounts[0]++;
            }} else if (meanTimeMs < 100) {{
                performanceCounts[1]++;
            }} else {{
                performanceCounts[2]++;
            }}
        }});
        
        var pieData = [{{
            values: performanceCounts,
            labels: ['Excellent (<1ms)', 'Moderate (1-100ms)', 'Slow (>100ms)'],
            type: 'pie',
            marker: {{
                colors: categoryColors
            }},
            textinfo: 'label+percent',
            textposition: 'outside'
        }}];
        
        var pieLayout = {{
            title: 'Performance Distribution',
            showlegend: true,
            height: 500,
            margin: {{
                l: 20,
                r: 20,
                t: 60,
                b: 20
            }}
        }};
        
        Plotly.newPlot('pie-chart', pieData, pieLayout);
        
        // Performance scatter plot showing variability
        var scatterData = [{{
            x: benchmarks.map(b => b.name),
            y: benchmarks.map(b => b.stats.mean * 1000),
            error_y: {{
                type: 'data',
                array: benchmarks.map(b => (b.stats.max - b.stats.min) * 1000),
                visible: true
            }},
            type: 'scatter',
            mode: 'markers+error',
            marker: {{
                size: benchmarks.map(b => Math.log(b.stats.rounds + 1) * 5),
                color: benchmarks.map(b => b.stats.mean * 1000),
                colorscale: 'RdYlGn',
                reversescale: true,
                showscale: true,
                colorbar: {{
                    title: 'Execution Time (ms)'
                }}
            }},
            name: 'Performance vs Variability'
        }}];
        
        var scatterLayout = {{
            title: 'Performance vs Variability (Error bars show min/max range)',
            xaxis: {{ 
                title: 'Benchmark', 
                tickangle: -45,
                automargin: true
            }},
            yaxis: {{ title: 'Mean Time (ms)', type: 'log' }},
            height: 600,
            margin: {{
                l: 80,
                r: 30,
                t: 80,
                b: 150
            }}
        }};
        
        Plotly.newPlot('performance-distribution', scatterData, scatterLayout);
        
        // Detailed table with performance classification
        var tableHTML = `
        <h2>&#128221; Detailed Benchmark Results</h2>
        <div class="explanation">
            <p><strong>Understanding the Table:</strong> Each row represents a different Hazelbean operation. 
            The performance classification helps you quickly identify which operations might need optimization.</p>
        </div>
        <table>
            <tr>
                <th>Benchmark Name</th>
                <th>What It Tests</th>
                <th>Mean Time</th>
                <th>Min Time</th>
                <th>Max Time</th>
                <th>Rounds</th>
                <th>Performance</th>
            </tr>
        `;
        
        var benchmarks = {benchmarks};
        
        // Function to classify performance
        function getPerformanceClass(meanTime) {{
            if (meanTime < 1) return {{ class: 'success', label: '&#128640; Excellent', description: 'Very fast operation' }};
            else if (meanTime < 100) return {{ class: 'warning', label: '&#9888; Moderate', description: 'Acceptable performance' }};
            else return {{ class: 'danger', label: '&#128012; Slow', description: 'Consider optimization' }};
        }}
        
        // Function to describe what each benchmark tests
        function getBenchmarkDescription(name) {{
            if (name.includes('array_operations')) return 'Creates 1000×1000 NumPy arrays, performs addition, multiplication, calculates mean';
            else if (name.includes('file_io')) return 'Writes/reads 9KB text file, measures I/O performance';
            else if (name.includes('path_resolution')) return 'Single ProjectFlow path resolution call';
            else if (name.includes('array_processing')) return 'Processes 500×500 array in 50×50 chunks (100 chunks total)';
            else if (name.includes('get_path')) return '10 consecutive Hazelbean path resolution calls';
            else if (name.includes('tiling')) return 'Spatial data tiling operations';
            else return 'Core Hazelbean functionality';
        }}
        

        
        benchmarks.forEach(function(benchmark) {{
            var meanTimeMs = benchmark.stats.mean * 1000;
            var perfClass = getPerformanceClass(meanTimeMs);
            var description = getBenchmarkDescription(benchmark.name);
            
            var rowClass = '';
            if (perfClass.class === 'success') rowClass = 'style="background-color: #d4edda; border-left: 3px solid #28a745;"';
            else if (perfClass.class === 'warning') rowClass = 'style="background-color: #fff3cd; border-left: 3px solid #ffc107;"';
            else if (perfClass.class === 'danger') rowClass = 'style="background-color: #f8d7da; border-left: 3px solid #dc3545;"';
            
            tableHTML += `
            <tr ${{rowClass}}>
                <td class="benchmark-name">${{benchmark.name}}</td>
                <td>${{description}}</td>
                <td><strong>${{meanTimeMs.toFixed(3)}}ms</strong></td>
                <td>${{(benchmark.stats.min * 1000).toFixed(3)}}ms</td>
                <td>${{(benchmark.stats.max * 1000).toFixed(3)}}ms</td>
                <td>${{benchmark.stats.rounds}}</td>
                <td><strong>${{perfClass.label}}</strong><br/><small>${{perfClass.description}}</small></td>
            </tr>
            `;
        }});
        
        tableHTML += '</table>';
        tableHTML += `
        <div class="explanation">
            <h4>💡 Tips for Using This Data:</h4>
            <ul>
                <li><strong>Focus on frequently used operations:</strong> Optimize slow benchmarks that your code calls often</li>
                <li><strong>Compare over time:</strong> Run benchmarks regularly to catch performance regressions</li>
                <li><strong>Consider the context:</strong> File I/O operations will naturally be slower than pure computations</li>
                <li><strong>Look at variability:</strong> Large differences between min and max times may indicate inconsistent performance</li>
            </ul>
        </div>
        `;
        
        document.getElementById('detailed-table').innerHTML = tableHTML;
        
        // Add benchmark count and recommendations
        document.addEventListener('DOMContentLoaded', function() {{
            // Add dynamic recommendations based on the data
            var slowBenchmarks = benchmarks.filter(b => (b.stats.mean * 1000) > 100);
            if (slowBenchmarks.length > 0) {{
                var recommendationHTML = `
                <div class="warning" style="margin-top: 30px;">
                    <h4>&#9888; Performance Recommendations</h4>
                    <p>Found ${{slowBenchmarks.length}} benchmark(s) with execution time > 100ms:</p>
                    <ul>
                `;
                slowBenchmarks.forEach(b => {{
                    recommendationHTML += `<li><strong>${{b.name}}</strong>: ${{(b.stats.mean * 1000).toFixed(3)}}ms - Consider optimization</li>`;
                }});
                recommendationHTML += `
                    </ul>
                    <p><strong>Next Steps:</strong> Profile these functions to identify bottlenecks, consider algorithm improvements, or implement caching strategies.</p>
                </div>
                `;
                document.body.appendChild(document.createElement('div')).innerHTML = recommendationHTML;
            }} else {{
                var successHTML = `
                <div class="success" style="margin-top: 30px;">
                    <h4>🎉 Great Performance!</h4>
                    <p>All benchmarks are performing well (< 100ms). Your code is well optimized!</p>
                </div>
                `;
                document.body.appendChild(document.createElement('div')).innerHTML = successHTML;
            }}
        }});
    </script>
    </div>
</body>
</html>
    """
    
    with open(output_html, 'w') as f:
        f.write(html_content)
    
    print(f"✅ HTML dashboard created: {output_html}")
    
    if start_server:
        # Find an available port
        port = find_free_port()
        if port is None:
            print("⚠️ Could not find an available port, opening as file instead")
            file_url = f"file://{os.path.abspath(output_html)}"
            print(f"🌐 Open in browser: {file_url}")
            try:
                webbrowser.open(file_url)
            except Exception as e:
                print(f"⚠️ Could not auto-open browser: {e}")
            return
        
        # Start server in background thread
        server_thread = threading.Thread(
            target=start_local_server, 
            args=(port, os.getcwd()),
            daemon=True
        )
        server_thread.start()
        
        # Give server a moment to start
        import time
        time.sleep(0.5)
        
        # Open browser to localhost URL
        dashboard_url = f"http://localhost:{port}/benchmark_dashboard.html"
        try:
            webbrowser.open(dashboard_url)
            print(f"🌐 Dashboard opened in browser at {dashboard_url}")
        except Exception as e:
            print(f"⚠️ Could not auto-open browser: {e}")
            print(f"💡 Manually open: {dashboard_url}")
        
        # Keep the main thread alive so server stays running
        try:
            print("\n🔄 Server running... Press Ctrl+C to stop")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping server...")
    else:
        file_url = f"file://{os.path.abspath(output_html)}"
        print(f"🌐 Open in browser: {file_url}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create interactive benchmark dashboard")
    parser.add_argument('json_file', nargs='?', help='Benchmark JSON file (or latest if not specified)')
    parser.add_argument('--no-server', action='store_true', help='Create HTML only, do not start server')
    parser.add_argument('--port', type=int, default=8080, help='Server port (default: 8080)')
    
    args = parser.parse_args()
    
    if not args.json_file:
        # Find latest benchmark file
        metrics_dir = "./metrics"
        if not os.path.exists(metrics_dir):
            print("❌ No metrics directory found")
            sys.exit(1)
            
        # Look for benchmark files in organized benchmarks subdirectory
        benchmarks_dir = os.path.join(metrics_dir, 'benchmarks')
        if not os.path.exists(benchmarks_dir):
            print("❌ No benchmarks directory found")
            sys.exit(1)
            
        json_files = [f for f in os.listdir(benchmarks_dir) if f.startswith('benchmark_') and f.endswith('.json')]
        if not json_files:
            print("❌ No benchmark files found")
            sys.exit(1)
            
        json_file = os.path.join(benchmarks_dir, max(json_files, key=lambda f: os.path.getmtime(os.path.join(benchmarks_dir, f))))
    else:
        json_file = args.json_file
    
    create_html_dashboard(json_file, start_server=not args.no_server)
