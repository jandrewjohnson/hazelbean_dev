#!/usr/bin/env python3
"""
Hazelbean Architecture Diagram Generator

Creates a comprehensive architecture diagram using Graphviz
Focuses on areas relevant to the testing pipeline sprint
"""

import graphviz
from pathlib import Path
import sys
import os

def create_hazelbean_architecture_diagram():
    """
    Creates a comprehensive architecture diagram for Hazelbean
    Focuses on areas relevant to the testing pipeline sprint
    """
    
    # Create the main diagram
    dot = graphviz.Digraph('hazelbean_architecture', comment='Hazelbean Architecture')
    dot.attr(rankdir='TB', size='16,12', dpi='300')
    dot.attr('node', shape='box', style='rounded,filled', fontname='Arial')
    dot.attr('edge', fontname='Arial', fontsize='10')

    # Define color scheme for different layers
    colors = {
        'user': '#E8F4FD',      # Light blue
        'project': '#FFF2CC',    # Light yellow  
        'processing': '#E1F5FE', # Light cyan
        'data': '#F3E5F5',       # Light purple
        'external': '#EFEBE9',   # Light brown
        'testing': '#FFEBEE',    # Light red
        'core': '#E8F5E8'        # Light green
    }

    # User Interface Layer
    with dot.subgraph(name='cluster_ui') as ui:
        ui.attr(label='User Interface Layer', style='filled', color=colors['user'])
        ui.node('jupyter', 'Jupyter\\nNotebooks', color=colors['user'])
        ui.node('cli', 'CLI Tools\\n(cli.py)', color=colors['user'])
        ui.node('gui', 'Qt GUI\\n(ui/)', color=colors['user'])
        ui.node('api', 'Python API\\n(import hazelbean)', color=colors['user'])

    # ProjectFlow Management Layer (KEY TESTING FOCUS)
    with dot.subgraph(name='cluster_projectflow') as pf:
        pf.attr(label='ProjectFlow Management Layer (🎯 Testing Focus)', 
                style='filled', color=colors['project'], fontcolor='red')
        pf.node('projectflow', 'ProjectFlow Object\\n• Task orchestration\\n• Directory management\\n• Dependency resolution', 
                color=colors['project'], style='filled,bold')
        pf.node('get_path', 'get_path() System\\n• Local file resolution\\n• Cloud storage integration\\n• Base data hierarchy', 
                color=colors['testing'], style='filled,bold')
        pf.node('task_mgmt', 'Task Management\\n• add_task()\\n• run_task()\\n• Parallel execution', 
                color=colors['project'], style='filled,bold')
        pf.node('tiling', 'Tiling Iterator\\n• Spatial chunking\\n• Parallel processing\\n• Memory management', 
                color=colors['testing'], style='filled,bold')

    # Core Processing Modules
    with dot.subgraph(name='cluster_processing') as proc:
        proc.attr(label='Geospatial Processing Layer', style='filled', color=colors['processing'])
        proc.node('raster', 'Raster Operations\\n• pyramids.py\\n• cog.py\\n• pog.py', color=colors['processing'])
        proc.node('vector', 'Vector Operations\\n• vector.py\\n• geoprocessing_extension.py', color=colors['processing'])
        proc.node('spatial', 'Spatial Utilities\\n• spatial_utils.py\\n• spatial_projection.py', color=colors['processing'])
        proc.node('file_io', 'File I/O\\n• file_io.py\\n• Format conversion', color=colors['processing'])

    # Data Structure & Analysis Layer
    with dot.subgraph(name='cluster_data') as data:
        data.attr(label='Data Structure & Analysis Layer', style='filled', color=colors['data'])
        data.node('arrayframe', 'ArrayFrame\\n• Spatial DataFrames\\n• Geo-aware operations', color=colors['data'])
        data.node('stats', 'Statistics\\n• stats.py\\n• RegressionFrame', color=colors['data'])
        data.node('calc_core', 'Calculation Core\\n• Cython functions\\n• High-performance ops', color=colors['data'])
        data.node('viz', 'Visualization\\n• matplotlib integration\\n• seaborn, cartopy', color=colors['data'])

    # External Dependencies
    with dot.subgraph(name='cluster_external') as ext:
        ext.attr(label='External Dependencies', style='filled', color=colors['external'])
        ext.node('gdal', 'GDAL/OGR\\nGeopandas\\nShapely', color=colors['external'])
        ext.node('numpy', 'NumPy/SciPy\\nPandas\\nXarray', color=colors['external'])
        ext.node('cloud', 'Google Cloud\\n• Storage\\n• Authentication', color=colors['testing'], style='filled,bold')
        ext.node('parallel', 'Parallel Computing\\n• TaskGraph\\n• multiprocessing\\n• Dask', color=colors['external'])

    # Testing Infrastructure (New - Your Sprint Focus)
    with dot.subgraph(name='cluster_testing') as test:
        test.attr(label='Testing Infrastructure (🚀 Sprint Goal)', 
                 style='filled', color=colors['testing'], fontcolor='red')
        test.node('pytest', 'pytest Framework\\n• pytest-benchmark\\n• pytest-cov\\n• Coverage reporting', 
                 color=colors['testing'], style='filled,bold')
        test.node('vignettes', 'Quarto Vignettes\\n• .qmd generation\\n• Educational docs\\n• Static parsing', 
                 color=colors['testing'], style='filled,bold')
        test.node('ci_cd', 'CI/CD Pipeline\\n• GitHub Actions\\n• Quality gates\\n• Automated testing', 
                 color=colors['testing'], style='filled,bold')

    # Core Utilities
    with dot.subgraph(name='cluster_core') as core:
        core.attr(label='Core Utilities', style='filled', color=colors['core'])
        core.node('config', 'Configuration\\n• config.py\\n• globals.py', color=colors['core'])
        core.node('utils', 'General Utils\\n• utils.py\\n• os_utils.py', color=colors['core'])
        core.node('logging', 'Logging System\\n• Custom loggers\\n• Performance timing', color=colors['core'])

    # Define relationships - User Interface connections
    for ui_node in ['jupyter', 'cli', 'gui', 'api']:
        dot.edge(ui_node, 'projectflow', label='uses')

    # ProjectFlow internal relationships
    dot.edge('projectflow', 'get_path', label='manages', color='red', style='bold')
    dot.edge('projectflow', 'task_mgmt', label='orchestrates', color='red', style='bold')
    dot.edge('projectflow', 'tiling', label='controls', color='red', style='bold')
    dot.edge('get_path', 'cloud', label='resolves', color='red', style='bold')

    # Processing layer connections
    dot.edge('task_mgmt', 'raster', label='executes')
    dot.edge('task_mgmt', 'vector', label='executes')
    dot.edge('task_mgmt', 'spatial', label='executes')
    dot.edge('tiling', 'raster', label='chunks', color='red')
    dot.edge('tiling', 'parallel', label='parallelizes', color='red')

    # Data flow connections
    dot.edge('raster', 'arrayframe', label='creates')
    dot.edge('vector', 'arrayframe', label='creates')
    dot.edge('arrayframe', 'stats', label='analyzes')
    dot.edge('arrayframe', 'viz', label='visualizes')

    # File I/O connections
    dot.edge('get_path', 'file_io', label='locates', color='red', style='bold')
    dot.edge('file_io', 'raster', label='loads')
    dot.edge('file_io', 'vector', label='loads')

    # External dependencies
    dot.edge('raster', 'gdal', label='depends on')
    dot.edge('vector', 'gdal', label='depends on')
    dot.edge('arrayframe', 'numpy', label='depends on')
    dot.edge('stats', 'numpy', label='depends on')
    dot.edge('calc_core', 'numpy', label='accelerates')

    # Core utilities connections
    dot.edge('projectflow', 'config', label='configures')
    dot.edge('projectflow', 'utils', label='utilizes')
    dot.edge('projectflow', 'logging', label='logs to')

    # Testing connections (Your Sprint Focus)
    dot.edge('pytest', 'projectflow', label='tests', color='red', style='bold')
    dot.edge('pytest', 'get_path', label='validates', color='red', style='bold')
    dot.edge('pytest', 'tiling', label='benchmarks', color='red', style='bold')
    dot.edge('vignettes', 'pytest', label='documents', color='red', style='bold')
    dot.edge('ci_cd', 'pytest', label='automates', color='red', style='bold')

    return dot

def main():
    """Generate the architecture diagram in multiple formats"""
    print("🏗️  Generating Hazelbean Architecture Diagram...")
    
    # Create the diagram
    diagram = create_hazelbean_architecture_diagram()
    
    # Determine output directory (same as script location)
    output_dir = Path(__file__).parent
    
    try:
        # Generate PNG for presentations
        diagram.render(output_dir / 'hazelbean_architecture', format='png', cleanup=True)
        print(f"✅ PNG generated: {output_dir / 'hazelbean_architecture.png'}")
        
        # Generate SVG for web/documentation
        diagram.render(output_dir / 'hazelbean_architecture', format='svg', cleanup=True)
        print(f"✅ SVG generated: {output_dir / 'hazelbean_architecture.svg'}")
        
        # Generate PDF for high-quality prints
        diagram.render(output_dir / 'hazelbean_architecture', format='pdf', cleanup=True)
        print(f"✅ PDF generated: {output_dir / 'hazelbean_architecture.pdf'}")
        
        # Save DOT source for version control
        with open(output_dir / 'hazelbean_architecture.dot', 'w') as f:
            f.write(diagram.source)
        print(f"✅ DOT source saved: {output_dir / 'hazelbean_architecture.dot'}")
        
        print(f"\n🎉 Architecture diagram generated successfully!")
        print(f"📁 Files saved to: {output_dir.absolute()}")
        
    except Exception as e:
        print(f"❌ Error generating diagram: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Install Graphviz: brew install graphviz (macOS) or apt-get install graphviz (Linux)")
        print("2. Install Python package: pip install graphviz")
        print("3. Ensure Graphviz is in your PATH")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
