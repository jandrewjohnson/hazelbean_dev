# Testing Infrastructure Utilities

This directory contains utility scripts for managing the test architecture foundation and migration processes.

## Available Utilities

### Foundation Validator (`foundation_validator.py`)
Validates that the test architecture foundation is correctly implemented.

**Features:**
- Validates complete directory structure
- Checks conftest.py file validity
- Verifies pytest configuration
- Validates test discovery functionality
- Checks README documentation

**Usage:**
```bash
python foundation_validator.py [--verbose]
```

### Migration Checkpoint (`migration_checkpoint.py`)
Creates and manages checkpoints during test infrastructure migration.

**Features:**
- Creates timestamped checkpoints with metadata
- Captures directory state and git information
- Validates checkpoint integrity
- Lists all available checkpoints

**Usage:**
```bash
# Create checkpoint
python migration_checkpoint.py create "Checkpoint Name" [--description "Optional description"]

# List checkpoints
python migration_checkpoint.py list

# Validate checkpoint
python migration_checkpoint.py validate <checkpoint_id>
```

### Rollback Manager (`rollback_manager.py`)
Provides safe rollback capabilities for test infrastructure migration.

**Features:**
- Safe rollback to any checkpoint state
- Dry-run capability for testing
- Pre-rollback backup creation
- Emergency restore functionality

**Usage:**
```bash
# List rollback candidates
python rollback_manager.py list-checkpoints

# Test rollback (dry-run)
python rollback_manager.py rollback <checkpoint_id> --dry-run

# Perform rollback
python rollback_manager.py rollback <checkpoint_id> [--force]

# Create manual backup
python rollback_manager.py create-backup "Backup Name"

# Emergency restore
python rollback_manager.py emergency-restore
```

## Integration with Migration Workflow

These utilities are designed to work together throughout the migration process:

1. **Before Migration Phase**: Create checkpoint
2. **During Migration**: Make changes with confidence 
3. **After Migration**: Validate foundation and test discovery
4. **If Issues**: Rollback to previous working state

## Examples

### Complete Migration Workflow
```bash
# 1. Create checkpoint before starting
python migration_checkpoint.py create "Before Story 3" --description "Starting QMD automation consolidation"

# 2. Make migration changes...

# 3. Validate foundation after changes
python foundation_validator.py --verbose

# 4. If validation fails, rollback
python rollback_manager.py rollback 20250903_123456_Before_Story_3

# 5. If validation passes, create completion checkpoint
python migration_checkpoint.py create "Story 3 Complete"
```

### Emergency Recovery
```bash
# If system is in broken state and no checkpoints work
python rollback_manager.py emergency-restore
```

## Best Practices

1. **Always Create Checkpoints** before major changes
2. **Test Rollback Procedures** with --dry-run first
3. **Validate Foundation** after each migration phase
4. **Use Descriptive Names** for checkpoints and backups
5. **Check Test Discovery** after structural changes

## Files Generated

### Checkpoints Directory
- Location: `/.migration_checkpoints/`
- Contains: Timestamped directories with metadata and backups
- Structure: `YYYYMMDD_HHMMSS_Checkpoint_Name/`

### Checkpoint Contents
- `metadata.json` - Complete state information
- `backups/` - Critical configuration file backups
- Directory state snapshot and file hashes

### Validation Reports
- Console output with detailed validation results
- Error/warning categorization
- Actionable recommendations for fixes
