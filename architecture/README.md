# Hazelbean Architecture Documentation

This directory contains architecture diagrams and documentation for the Hazelbean geospatial processing library.

## Files

- **`generate_diagram.py`** - Python script to generate architecture diagrams using Graphviz
- **`hazelbean_architecture.dot`** - Raw Graphviz DOT source file (version controlled)
- **`hazelbean_architecture.png`** - High-resolution PNG for presentations
- **`hazelbean_architecture.svg`** - Scalable vector format for web documentation
- **`hazelbean_architecture.pdf`** - High-quality PDF for printing

## Quick Start

### Prerequisites

1. **Install Graphviz**:
   ```bash
   # macOS
   brew install graphviz
   
   # Ubuntu/Debian
   sudo apt-get install graphviz
   
   # Windows
   # Download from: https://graphviz.org/download/
   ```

2. **Install Python package**:
   ```bash
   pip install graphviz
   ```

### Generate Diagrams

```bash
cd architecture/
python generate_diagram.py
```

This will create all output formats (PNG, SVG, PDF) in the current directory.

### Manual Generation (using DOT file)

```bash
# PNG format
dot -Tpng hazelbean_architecture.dot -o hazelbean_architecture.png

# SVG format  
dot -Tsvg hazelbean_architecture.dot -o hazelbean_architecture.svg

# PDF format
dot -Tpdf hazelbean_architecture.dot -o hazelbean_architecture.pdf
```

## Architecture Overview

The Hazelbean architecture diagram highlights:

### 🎯 **Testing Focus Areas** (Sprint Goal)
- **ProjectFlow Management**: Core orchestration system
- **get_path() System**: File resolution (local + cloud)
- **Tiling Iterator**: Spatial chunking and parallel processing
- **Testing Infrastructure**: pytest, coverage, CI/CD pipeline

### 🏗️ **Layer Structure**
1. **User Interface**: Jupyter, CLI, Qt GUI, Python API
2. **ProjectFlow Management**: Task orchestration and dependency resolution
3. **Geospatial Processing**: Raster/vector operations, spatial utilities
4. **Data & Analysis**: ArrayFrame, statistics, visualization
5. **External Dependencies**: GDAL, NumPy, Google Cloud, parallel computing

### 🔗 **Key Relationships**
- **Red bold edges**: Primary testing targets
- **Color coding**: Functional areas and dependencies
- **Cluster organization**: Logical component grouping

## Usage in Documentation

### For Class Demonstrations
- Use the **PNG format** for presentations
- Highlight the testing infrastructure cluster
- Explain the ProjectFlow-centric architecture

### For Developer Onboarding
- Reference the **SVG version** in web documentation
- Point new developers to the core utilities and ProjectFlow layers
- Emphasize the get_path() system for data management

### For Technical Documentation
- Include the **DOT source** in version control
- Use the **PDF version** for high-quality prints
- Link to specific modules shown in the diagram

## Customization

To modify the diagram:

1. **Edit the Python script** (`generate_diagram.py`) for complex changes
2. **Edit the DOT file** (`hazelbean_architecture.dot`) for simple text/color changes
3. **Regenerate** using either method above

### Color Scheme
- Light Blue (`#E8F4FD`): User Interface
- Light Yellow (`#FFF2CC`): ProjectFlow Management
- Light Cyan (`#E1F5FE`): Geospatial Processing
- Light Purple (`#F3E5F5`): Data & Analysis
- Light Brown (`#EFEBE9`): External Dependencies
- Light Red (`#FFEBEE`): Testing Infrastructure
- Light Green (`#E8F5E8`): Core Utilities

## Integration with Testing Pipeline

This architecture diagram is specifically designed to support the **Hazelbean Test Pipeline Sprint**:

- **Educational Value**: Clear visualization for class demonstrations
- **Testing Documentation**: Shows what components are being tested
- **CI/CD Integration**: Can be regenerated automatically in GitHub Actions
- **Developer Onboarding**: Helps new contributors understand the codebase structure

## Maintenance

- **Update after major refactoring**: Keep the diagram synchronized with code changes
- **Version control**: The DOT file ensures diagram changes are tracked
- **Automated generation**: Consider adding to CI pipeline for documentation updates
