# Hazelbean Educational Content Generator

Simple tool to generate QMD tutorial files from educational examples. Replaces the complex 58-file QMD automation system with a focused, maintainable educational-only generator.

## Quick Start

```bash
# From anywhere in the project (config auto-detected):
python tools/education/generate.py

# View generated content
ls docs/educational/

# Activate environment and render with Quarto
conda activate hazelbean_env
cd docs/educational && quarto render *.qmd
```

## Features

- **Simple & Fast**: ~200 lines total, generates content in <30 seconds
- **Educational Focus**: Optimized for learning, not testing
- **Progressive Tutorials**: Creates step-by-step learning sequence
- **Quarto Ready**: Output renders perfectly in Quarto sites
- **Easy Maintenance**: Professors can understand and modify in 10 minutes
- **Smart Configuration**: Auto-detects config.yaml from anywhere in the project

## Usage

### Basic Generation
```bash
# Works from anywhere in the project (config auto-detected):
python tools/education/generate.py                      # Generate all tutorials
python tools/education/generate.py --steps step_1,step_3 # Generate specific steps
python tools/education/generate.py --dry-run             # Preview generation

# From tools/education/ directory (shorter commands):
cd tools/education
python generate.py                           # Generate all tutorials
python generate.py --steps step_1,step_3     # Generate specific steps
python generate.py --dry-run                 # Preview generation

# Custom config or output directory
python tools/education/generate.py --config /path/to/custom.yaml
python tools/education/generate.py --output /path/to/output
```

### Configuration

Edit `config.yaml` to customize:
- Tutorial metadata and descriptions
- Learning time estimates  
- Key concepts for each step
- Output directory and formatting options

### Generated Output

The generator creates:
- `step_1.qmd` through `step_5.qmd` - Individual tutorial pages
- `index.qmd` - Learning path overview with navigation
- Proper Quarto metadata for site integration

## File Structure

```
tools/education/
├── generate.py              # Main generator (150 lines)
├── config.yaml             # Step configuration (30 lines)
├── templates/
│   ├── step_template.qmd.j2    # Tutorial page template (80 lines)
│   └── index_template.qmd.j2   # Index page template (40 lines)
└── README.md               # This file (20 lines)
```

## Dependencies

- Python 3.6+
- PyYAML (`pip install pyyaml`)
- Jinja2 (`pip install jinja2`)
- Existing educational examples in `examples/step_*.py`

## Rendering with Quarto

After generation, render to HTML:

```bash
# Activate the conda environment first
conda activate hazelbean_env

# Then render individual files
cd docs/educational
quarto render *.qmd

# Or render specific files
quarto render index.qmd step_1.qmd step_2.qmd
```

## Design Principles

- **Simple over comprehensive** - Educational focus only
- **Maintainable over feature-rich** - Professors can understand and modify
- **Clear over clever** - Readable code, obvious behavior
- **Fast over perfect** - Quick generation for iterative content development

---

*Generated content is based on educational examples in `examples/step_*.py`. Modify those files to update tutorial content.*
