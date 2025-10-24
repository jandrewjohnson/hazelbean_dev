# Testing Infrastructure Tools

Testing infrastructure, fixtures, and utility functions.

## Directory Structure

- `qmd_automation/` - Documentation automation system (moved from root)
- `fixtures/` - Shared test fixtures
- `data/` - Test data management
- `utilities/` - Test utility functions

## QMD Automation System

The QMD automation system generates browser-viewable documentation from tests with intelligent path resolution and data dependency handling.

**✨ Enhanced Features:**
- **Automatic path resolution**: Converts `../../../data` → `../../data` for QMD context
- **sys.path cleanup**: Removes import hacks like `sys.path.extend(['../../../'])`
- **Data dependency validation**: Verifies file availability and provides detailed metadata
- **Cross-context compatibility**: Generated examples work from both test and docs directories

See `qmd_automation/docs/` for detailed documentation and implementation details.

## Running Tools

```bash
# Run QMD automation CLI
python -m hazelbean_tests.tools.qmd_automation --help

# Use fixtures in tests
from hazelbean_tests.tools.fixtures import common_fixtures
```
