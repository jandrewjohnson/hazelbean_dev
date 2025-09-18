#!/usr/bin/env python
"""
Migration Checkpoint Script

Creates checkpoints during test infrastructure migration to enable
safe rollback and validation of each migration phase.

Usage:
    python migration_checkpoint.py create "Phase 1 Complete"
    python migration_checkpoint.py list
    python migration_checkpoint.py validate <checkpoint_id>
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

class MigrationCheckpoint:
    """Manages migration checkpoints for safe test infrastructure changes."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent.parent.parent
        self.checkpoint_dir = self.root_dir / ".migration_checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)
        
    def create_checkpoint(self, name, description=""):
        """Create a new migration checkpoint."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_id = f"{timestamp}_{self._sanitize_name(name)}"
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        checkpoint_path.mkdir(exist_ok=True)
        
        # Create metadata
        metadata = {
            "id": checkpoint_id,
            "name": name,
            "description": description,
            "created": datetime.now().isoformat(),
            "git_commit": self._get_git_commit(),
            "directory_state": self._capture_directory_state(),
            "pytest_config": self._capture_pytest_config(),
            "test_counts": self._count_tests()
        }
        
        with open(checkpoint_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
            
        # Backup critical files
        self._backup_critical_files(checkpoint_path)
        
        print(f"✅ Created checkpoint: {checkpoint_id}")
        print(f"   Name: {name}")
        print(f"   Path: {checkpoint_path}")
        
        return checkpoint_id
        
    def list_checkpoints(self):
        """List all available checkpoints."""
        if not self.checkpoint_dir.exists():
            print("No checkpoints found.")
            return []
            
        checkpoints = []
        for checkpoint_path in self.checkpoint_dir.iterdir():
            if checkpoint_path.is_dir():
                metadata_file = checkpoint_path / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        checkpoints.append(metadata)
                    except Exception as e:
                        print(f"Warning: Cannot read checkpoint {checkpoint_path}: {e}")
                        
        checkpoints.sort(key=lambda x: x['created'], reverse=True)
        
        if not checkpoints:
            print("No valid checkpoints found.")
        else:
            print(f"Found {len(checkpoints)} checkpoints:")
            print("-" * 80)
            for cp in checkpoints:
                print(f"ID: {cp['id']}")
                print(f"Name: {cp['name']}")
                print(f"Created: {cp['created']}")
                print(f"Tests: {cp.get('test_counts', {}).get('total', 'unknown')}")
                print(f"Description: {cp.get('description', 'No description')}")
                print("-" * 80)
                
        return checkpoints
        
    def validate_checkpoint(self, checkpoint_id):
        """Validate a specific checkpoint."""
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        if not checkpoint_path.exists():
            print(f"❌ Checkpoint not found: {checkpoint_id}")
            return False
            
        metadata_file = checkpoint_path / "metadata.json"
        if not metadata_file.exists():
            print(f"❌ Checkpoint metadata not found: {checkpoint_id}")
            return False
            
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                
            print(f"Validating checkpoint: {checkpoint_id}")
            print("-" * 40)
            
            # Validate metadata structure
            required_fields = ['id', 'name', 'created', 'directory_state', 'test_counts']
            missing_fields = [f for f in required_fields if f not in metadata]
            if missing_fields:
                print(f"❌ Missing metadata fields: {missing_fields}")
                return False
                
            # Validate directory state
            current_state = self._capture_directory_state()
            stored_state = metadata['directory_state']
            
            state_changes = self._compare_directory_states(stored_state, current_state)
            if state_changes:
                print("📋 Directory changes since checkpoint:")
                for change in state_changes:
                    print(f"  {change}")
            else:
                print("✅ Directory structure unchanged")
                
            # Validate test discovery still works
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", "--collect-only", "-q"],
                    cwd=self.root_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print("✅ Test discovery working")
                else:
                    print(f"❌ Test discovery failed: {result.stderr}")
                    return False
                    
            except Exception as e:
                print(f"❌ Cannot validate test discovery: {e}")
                return False
                
            print(f"✅ Checkpoint {checkpoint_id} is valid")
            return True
            
        except Exception as e:
            print(f"❌ Error validating checkpoint: {e}")
            return False
            
    def _sanitize_name(self, name):
        """Sanitize name for use as directory name."""
        return "".join(c for c in name if c.isalnum() or c in "_- ").replace(" ", "_")
        
    def _get_git_commit(self):
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root_dir,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None
            
    def _capture_directory_state(self):
        """Capture the current test directory structure state."""
        test_dir = self.root_dir / "hazelbean_tests"
        if not test_dir.exists():
            return {"error": "hazelbean_tests directory not found"}
            
        state = {
            "directories": [],
            "files": {}
        }
        
        for root, dirs, files in os.walk(test_dir):
            rel_root = os.path.relpath(root, test_dir)
            
            # Record directories
            for dir_name in sorted(dirs):
                if not dir_name.startswith('.') and dir_name != '__pycache__':
                    rel_path = os.path.join(rel_root, dir_name) if rel_root != '.' else dir_name
                    state["directories"].append(rel_path)
                    
            # Record important files
            for file_name in sorted(files):
                if file_name.endswith(('.py', '.ini', '.md', '.yaml', '.yml', '.json')):
                    full_path = os.path.join(root, file_name)
                    rel_path = os.path.relpath(full_path, test_dir)
                    
                    try:
                        # Store file hash for change detection
                        with open(full_path, 'rb') as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()
                        state["files"][rel_path] = {
                            "hash": file_hash,
                            "size": os.path.getsize(full_path)
                        }
                    except Exception:
                        state["files"][rel_path] = {"error": "cannot_read"}
                        
        return state
        
    def _capture_pytest_config(self):
        """Capture current pytest configuration."""
        pytest_ini = self.root_dir / "pytest.ini"
        if pytest_ini.exists():
            try:
                with open(pytest_ini, 'r') as f:
                    content = f.read()
                return {
                    "exists": True,
                    "hash": hashlib.md5(content.encode()).hexdigest(),
                    "size": len(content)
                }
            except Exception:
                return {"exists": True, "error": "cannot_read"}
        else:
            return {"exists": False}
            
    def _count_tests(self):
        """Count tests in the current structure."""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                test_count = sum(1 for line in lines if '<Function' in line or '<Method' in line)
                return {"total": test_count, "discovery_success": True}
            else:
                return {"total": 0, "discovery_success": False, "error": result.stderr}
                
        except Exception as e:
            return {"total": 0, "discovery_success": False, "error": str(e)}
            
    def _backup_critical_files(self, checkpoint_path):
        """Backup critical configuration files."""
        backup_dir = checkpoint_path / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        critical_files = [
            "pytest.ini",
            "hazelbean_tests/conftest.py",
            "hazelbean_tests/unit/conftest.py",
            "hazelbean_tests/integration/conftest.py",
            "hazelbean_tests/performance/conftest.py",
            "hazelbean_tests/system/conftest.py"
        ]
        
        for file_path in critical_files:
            full_path = self.root_dir / file_path
            if full_path.exists():
                backup_file = backup_dir / file_path.replace("/", "_")
                try:
                    shutil.copy2(full_path, backup_file)
                except Exception as e:
                    print(f"Warning: Cannot backup {file_path}: {e}")
                    
    def _compare_directory_states(self, old_state, new_state):
        """Compare two directory states and return changes."""
        changes = []
        
        # Check for new/removed directories
        old_dirs = set(old_state.get("directories", []))
        new_dirs = set(new_state.get("directories", []))
        
        for new_dir in new_dirs - old_dirs:
            changes.append(f"Added directory: {new_dir}")
        for removed_dir in old_dirs - new_dirs:
            changes.append(f"Removed directory: {removed_dir}")
            
        # Check for changed files
        old_files = old_state.get("files", {})
        new_files = new_state.get("files", {})
        
        all_files = set(old_files.keys()) | set(new_files.keys())
        for file_path in all_files:
            if file_path not in old_files:
                changes.append(f"Added file: {file_path}")
            elif file_path not in new_files:
                changes.append(f"Removed file: {file_path}")
            elif old_files[file_path].get("hash") != new_files[file_path].get("hash"):
                changes.append(f"Modified file: {file_path}")
                
        return changes


def main():
    parser = argparse.ArgumentParser(description="Manage migration checkpoints")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create checkpoint
    create_parser = subparsers.add_parser("create", help="Create a new checkpoint")
    create_parser.add_argument("name", help="Checkpoint name")
    create_parser.add_argument("--description", "-d", default="", 
                             help="Optional description")
    
    # List checkpoints
    list_parser = subparsers.add_parser("list", help="List all checkpoints")
    
    # Validate checkpoint
    validate_parser = subparsers.add_parser("validate", help="Validate a checkpoint")
    validate_parser.add_argument("checkpoint_id", help="Checkpoint ID to validate")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    checkpoint_manager = MigrationCheckpoint()
    
    if args.command == "create":
        checkpoint_manager.create_checkpoint(args.name, args.description)
    elif args.command == "list":
        checkpoint_manager.list_checkpoints()
    elif args.command == "validate":
        success = checkpoint_manager.validate_checkpoint(args.checkpoint_id)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
