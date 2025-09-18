"""
Step 1: Project Setup and Directory Management
Learning Time: 5 minutes
Prerequisites: Basic Python knowledge

Learn how to initialize a Hazelbean ProjectFlow for organized geospatial workflows.
This is the foundation for all Hazelbean projects - it creates an organized directory 
structure and provides intelligent file path resolution.
"""

import os
import hazelbean as hb

def main():
    """
    Demonstrates ProjectFlow initialization and basic project organization.
    """
    
    # Create a new project with automatic directory structure
    # This will create the project directory if it doesn't exist
    project_name = 'hazelbean_tutorial'
    p = hb.ProjectFlow(project_name)
    
    print("=== Hazelbean Project Setup Demo ===")
    print(f"Project name: {project_name}")
    print(f"Project directory: {p.project_dir}")
    print()
    
    # ProjectFlow automatically creates these standard directories:
    print("=== Standard Project Directories ===")
    print(f"Input directory: {p.input_dir}")
    print(f"Intermediate directory: {p.intermediate_dir}")
    print(f"Output directory: {p.output_dir}")
    print()
    
    # Show data discovery paths (where ProjectFlow looks for files)
    print("=== Data Discovery Hierarchy ===")
    print("When you use p.get_path(), Hazelbean searches in this order:")
    print(f"1. Base data directory: {p.base_data_dir}")
    print(f"2. Model base data directory: {p.model_base_data_dir}")
    print(f"3. Project base data directory: {p.project_base_data_dir}")
    print(f"4. Current directory: {p.project_dir}")
    print()
    
    # Verify directories exist
    print("=== Directory Status ===")
    for dir_name, dir_path in [
        ("Input", p.input_dir),
        ("Intermediate", p.intermediate_dir), 
        ("Output", p.output_dir)
    ]:
        exists = "✓ EXISTS" if os.path.exists(dir_path) else "✗ CREATED"
        print(f"{dir_name:12}: {exists}")
    
    print()
    print("🎉 Project setup complete!")
    print("Next: Run step_2_data_loading.py to learn about intelligent file discovery")


if __name__ == "__main__":
    main()
