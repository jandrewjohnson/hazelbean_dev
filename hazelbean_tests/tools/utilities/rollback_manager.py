#!/usr/bin/env python
"""
Rollback Manager

Provides safe rollback capabilities for test infrastructure migration.
Can restore the system to any previous checkpoint state.

Usage:
    python rollback_manager.py list-checkpoints
    python rollback_manager.py rollback <checkpoint_id> [--dry-run] [--force]
    python rollback_manager.py create-backup "Pre-rollback backup"
"""

import os
import sys
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
import argparse
import subprocess

from migration_checkpoint import MigrationCheckpoint

class RollbackManager:
    """Manages safe rollback operations for test infrastructure."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent.parent.parent
        self.checkpoint_manager = MigrationCheckpoint()
        self.test_dir = self.root_dir / "hazelbean_tests"
        
    def create_pre_rollback_backup(self, checkpoint_id):
        """Create a backup before performing rollback."""
        backup_name = f"pre_rollback_{checkpoint_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return self.checkpoint_manager.create_checkpoint(
            backup_name, 
            f"Automatic backup before rolling back to {checkpoint_id}"
        )
        
    def rollback_to_checkpoint(self, checkpoint_id, dry_run=False, force=False):
        """Rollback the test infrastructure to a specific checkpoint."""
        print(f"{'[DRY RUN] ' if dry_run else ''}Rolling back to checkpoint: {checkpoint_id}")
        
        # Validate checkpoint exists and is valid
        checkpoint_path = self.checkpoint_manager.checkpoint_dir / checkpoint_id
        if not checkpoint_path.exists():
            print(f"❌ Checkpoint not found: {checkpoint_id}")
            return False
            
        metadata_file = checkpoint_path / "metadata.json"
        if not metadata_file.exists():
            print(f"❌ Checkpoint metadata not found")
            return False
            
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        except Exception as e:
            print(f"❌ Cannot read checkpoint metadata: {e}")
            return False
            
        # Validate checkpoint is valid
        if not self.checkpoint_manager.validate_checkpoint(checkpoint_id):
            if not force:
                print(f"❌ Checkpoint validation failed. Use --force to proceed anyway.")
                return False
            else:
                print("⚠️  Proceeding with invalid checkpoint due to --force flag")
                
        # Create pre-rollback backup
        if not dry_run:
            print("Creating pre-rollback backup...")
            backup_id = self.create_pre_rollback_backup(checkpoint_id)
            print(f"✅ Created backup: {backup_id}")
            
        # Perform rollback operations
        success = True
        
        # 1. Rollback directory structure
        if not self._rollback_directory_structure(metadata, dry_run):
            success = False
            
        # 2. Rollback configuration files
        if not self._rollback_configuration_files(checkpoint_path, dry_run):
            success = False
            
        # 3. Validate rollback
        if not dry_run and success:
            if not self._validate_rollback(metadata):
                print("❌ Rollback validation failed")
                success = False
                
        if success:
            print(f"✅ {'[DRY RUN] ' if dry_run else ''}Rollback completed successfully")
        else:
            print(f"❌ {'[DRY RUN] ' if dry_run else ''}Rollback failed")
            
        return success
        
    def _rollback_directory_structure(self, metadata, dry_run=False):
        """Rollback directory structure to checkpoint state."""
        print("Rolling back directory structure...")
        
        if "directory_state" not in metadata:
            print("❌ No directory state in checkpoint metadata")
            return False
            
        directory_state = metadata["directory_state"]
        if "error" in directory_state:
            print(f"❌ Checkpoint has directory state error: {directory_state['error']}")
            return False
            
        current_state = self.checkpoint_manager._capture_directory_state()
        target_dirs = set(directory_state.get("directories", []))
        current_dirs = set(current_state.get("directories", []))
        
        # Remove directories that shouldn't exist
        dirs_to_remove = current_dirs - target_dirs
        for dir_path in dirs_to_remove:
            full_path = self.test_dir / dir_path
            if full_path.exists() and full_path.is_dir():
                print(f"  {'[DRY RUN] ' if dry_run else ''}Removing directory: {dir_path}")
                if not dry_run:
                    try:
                        shutil.rmtree(full_path)
                    except Exception as e:
                        print(f"❌ Failed to remove directory {dir_path}: {e}")
                        return False
                        
        # Create directories that should exist
        dirs_to_create = target_dirs - current_dirs
        for dir_path in dirs_to_create:
            full_path = self.test_dir / dir_path
            print(f"  {'[DRY RUN] ' if dry_run else ''}Creating directory: {dir_path}")
            if not dry_run:
                try:
                    full_path.mkdir(parents=True, exist_ok=True)
                    # Create __init__.py if it's a Python package directory
                    if not dir_path.endswith(('__pycache__', '.benchmarks')):
                        init_file = full_path / "__init__.py"
                        if not init_file.exists():
                            init_file.touch()
                except Exception as e:
                    print(f"❌ Failed to create directory {dir_path}: {e}")
                    return False
                    
        return True
        
    def _rollback_configuration_files(self, checkpoint_path, dry_run=False):
        """Rollback configuration files from checkpoint backups."""
        print("Rolling back configuration files...")
        
        backup_dir = checkpoint_path / "backups"
        if not backup_dir.exists():
            print("⚠️  No configuration file backups found in checkpoint")
            return True  # Not necessarily an error
            
        # Map backup files to original locations
        file_mapping = {
            "pytest.ini": self.root_dir / "pytest.ini",
            "hazelbean_tests_conftest.py": self.test_dir / "conftest.py",
            "hazelbean_tests_unit_conftest.py": self.test_dir / "unit" / "conftest.py",
            "hazelbean_tests_integration_conftest.py": self.test_dir / "integration" / "conftest.py",
            "hazelbean_tests_performance_conftest.py": self.test_dir / "performance" / "conftest.py",
            "hazelbean_tests_system_conftest.py": self.test_dir / "system" / "conftest.py"
        }
        
        for backup_name, original_path in file_mapping.items():
            backup_file = backup_dir / backup_name
            if backup_file.exists():
                print(f"  {'[DRY RUN] ' if dry_run else ''}Restoring: {original_path}")
                if not dry_run:
                    try:
                        # Ensure parent directory exists
                        original_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(backup_file, original_path)
                    except Exception as e:
                        print(f"❌ Failed to restore {original_path}: {e}")
                        return False
                        
        return True
        
    def _validate_rollback(self, metadata):
        """Validate that rollback was successful."""
        print("Validating rollback...")
        
        # Check that pytest still works
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"❌ Test discovery failed after rollback: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Cannot validate test discovery after rollback: {e}")
            return False
            
        # Compare directory state to target
        current_state = self.checkpoint_manager._capture_directory_state()
        target_state = metadata.get("directory_state", {})
        
        changes = self.checkpoint_manager._compare_directory_states(target_state, current_state)
        if changes:
            print("⚠️  Directory state doesn't exactly match checkpoint:")
            for change in changes[:5]:  # Show first 5 changes
                print(f"  {change}")
            if len(changes) > 5:
                print(f"  ... and {len(changes) - 5} more changes")
            # This might be acceptable depending on use case
            
        return True
        
    def list_rollback_candidates(self):
        """List checkpoints available for rollback."""
        print("Available checkpoints for rollback:")
        print("=" * 60)
        
        checkpoints = self.checkpoint_manager.list_checkpoints()
        if not checkpoints:
            print("No checkpoints available for rollback.")
            return
            
        for cp in checkpoints:
            # Validate checkpoint before listing as candidate
            is_valid = self.checkpoint_manager.validate_checkpoint(cp['id'])
            status = "✅ Valid" if is_valid else "❌ Invalid"
            
            print(f"ID: {cp['id']}")
            print(f"Name: {cp['name']}")
            print(f"Status: {status}")
            print(f"Created: {cp['created']}")
            print(f"Git Commit: {cp.get('git_commit', 'Unknown')[:8]}")
            print("-" * 40)
            
    def emergency_restore(self):
        """Emergency restore to a minimal working state."""
        print("🚨 Performing emergency restore...")
        print("This will create a minimal working test directory structure.")
        
        # Create basic directory structure
        basic_structure = [
            "unit",
            "integration", 
            "performance",
            "system",
            "tools"
        ]
        
        for dir_name in basic_structure:
            dir_path = self.test_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                
            readme_file = dir_path / "README.md"
            if not readme_file.exists():
                with open(readme_file, 'w') as f:
                    f.write(f"# {dir_name.title()} Tests\n\nEmergency restore placeholder.\n")
                    
        # Create minimal pytest.ini
        pytest_ini = self.root_dir / "pytest.ini"
        if not pytest_ini.exists():
            minimal_config = """[tool:pytest]
testpaths = hazelbean_tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    system: System tests
"""
            with open(pytest_ini, 'w') as f:
                f.write(minimal_config)
                
        print("✅ Emergency restore completed.")
        print("Basic test directory structure created.")
        print("You may need to recreate specific configurations.")


def main():
    parser = argparse.ArgumentParser(description="Manage rollback operations")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List checkpoints
    list_parser = subparsers.add_parser("list-checkpoints", 
                                       help="List available rollback candidates")
    
    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", 
                                           help="Rollback to a checkpoint")
    rollback_parser.add_argument("checkpoint_id", help="Checkpoint ID to rollback to")
    rollback_parser.add_argument("--dry-run", action="store_true",
                                help="Show what would be done without making changes")
    rollback_parser.add_argument("--force", action="store_true",
                                help="Force rollback even if validation fails")
    
    # Create backup
    backup_parser = subparsers.add_parser("create-backup", 
                                         help="Create a backup checkpoint")
    backup_parser.add_argument("name", help="Backup name")
    
    # Emergency restore
    emergency_parser = subparsers.add_parser("emergency-restore",
                                           help="Emergency restore to minimal working state")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    rollback_manager = RollbackManager()
    
    if args.command == "list-checkpoints":
        rollback_manager.list_rollback_candidates()
    elif args.command == "rollback":
        success = rollback_manager.rollback_to_checkpoint(
            args.checkpoint_id, 
            dry_run=args.dry_run, 
            force=args.force
        )
        sys.exit(0 if success else 1)
    elif args.command == "create-backup":
        rollback_manager.checkpoint_manager.create_checkpoint(
            args.name, 
            "Manual backup created via rollback manager"
        )
    elif args.command == "emergency-restore":
        rollback_manager.emergency_restore()


if __name__ == "__main__":
    main()
