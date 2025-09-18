"""
Step 5: Export Results and Project Organization
Learning Time: 15 minutes
Prerequisites: Completed steps 1-4

Learn how to properly save geospatial results, organize outputs in the 
project structure, and create documentation for your analysis workflow.
"""

import os
import hazelbean as hb
import numpy as np
from datetime import datetime

def main():
    """
    Demonstrates proper result export and project organization.
    """
    
    # Initialize project (builds on previous steps)
    p = hb.ProjectFlow('hazelbean_tutorial')
    
    print("=== Hazelbean Results Export Demo ===")
    print()
    
    # Create some example results to export
    print("=== Generating Sample Results ===")
    
    # Create a sample analysis result
    rows, cols = 50, 50
    result_array = np.random.rand(rows, cols) * 100
    
    # Create a classification result
    classification = np.random.choice([1, 2, 3], size=(rows, cols), 
                                    p=[0.4, 0.4, 0.2])
    
    print(f"Generated results array: {result_array.shape}")
    print(f"Generated classification: {classification.shape}")
    
    # Set up proper output organization
    print()
    print("=== Organizing Output Structure ===")
    
    # Create timestamped analysis folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    analysis_dir = os.path.join(p.output_dir, f'tutorial_analysis_{timestamp}')
    
    # Create subdirectories for different output types
    rasters_dir = os.path.join(analysis_dir, 'rasters')
    reports_dir = os.path.join(analysis_dir, 'reports')
    
    for directory in [analysis_dir, rasters_dir, reports_dir]:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created: {os.path.relpath(directory, p.project_dir)}")
    
    # Export raster results (simulate proper geospatial export)
    print()
    print("=== Exporting Raster Results ===")
    
    # In a real workflow, you'd save with proper geospatial metadata
    # For this tutorial, we'll save as simple arrays with documentation
    
    results_file = os.path.join(rasters_dir, 'analysis_results.npy')
    np.save(results_file, result_array)
    print(f"✓ Saved results array: {os.path.basename(results_file)}")
    
    classification_file = os.path.join(rasters_dir, 'classification.npy')
    np.save(classification_file, classification)
    print(f"✓ Saved classification: {os.path.basename(classification_file)}")
    
    # Create metadata file
    metadata_file = os.path.join(rasters_dir, 'metadata.txt')
    with open(metadata_file, 'w') as f:
        f.write("Raster Metadata\n")
        f.write("===============\n")
        f.write(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Results shape: {result_array.shape}\n")
        f.write(f"Results range: {result_array.min():.2f} to {result_array.max():.2f}\n")
        f.write(f"Classification classes: {sorted(np.unique(classification))}\n")
        f.write("\nClass definitions:\n")
        f.write("1 = Low values\n")
        f.write("2 = Medium values\n") 
        f.write("3 = High values\n")
    
    print(f"✓ Created metadata: {os.path.basename(metadata_file)}")
    
    # Generate comprehensive analysis report
    print()
    print("=== Creating Analysis Report ===")
    
    report_file = os.path.join(reports_dir, 'tutorial_analysis_report.md')
    
    with open(report_file, 'w') as f:
        f.write("# Hazelbean Tutorial Analysis Report\n\n")
        
        f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Project:** {p.project_name}\n\n")
        
        f.write("## Summary\n\n")
        f.write("This analysis demonstrates the complete Hazelbean workflow from ")
        f.write("project setup through result export.\n\n")
        
        f.write("## Data Processing Steps\n\n")
        f.write("1. **Project Setup**: Initialized ProjectFlow with organized directories\n")
        f.write("2. **Data Loading**: Used get_path() for intelligent file discovery\n")
        f.write("3. **Processing**: Applied transformations and mathematical operations\n")
        f.write("4. **Analysis**: Performed spatial analysis and multi-raster operations\n")
        f.write("5. **Export**: Organized and documented results\n\n")
        
        f.write("## Results Summary\n\n")
        f.write(f"- **Results Array**: {result_array.shape} pixels\n")
        f.write(f"- **Value Range**: {result_array.min():.2f} to {result_array.max():.2f}\n")
        f.write(f"- **Mean Value**: {result_array.mean():.2f}\n")
        f.write(f"- **Standard Deviation**: {result_array.std():.2f}\n\n")
        
        f.write("## Classification Results\n\n")
        for class_val in sorted(np.unique(classification)):
            count = np.sum(classification == class_val)
            percent = (count / classification.size) * 100
            f.write(f"- **Class {class_val}**: {count} pixels ({percent:.1f}%)\n")
        
        f.write("\n## Files Generated\n\n")
        f.write("- `rasters/analysis_results.npy` - Main analysis results\n")
        f.write("- `rasters/classification.npy` - Classification map\n")
        f.write("- `rasters/metadata.txt` - Raster metadata\n")
        f.write("- `reports/tutorial_analysis_report.md` - This report\n\n")
        
        f.write("## Project Structure\n\n")
        f.write("```\n")
        f.write(f"{p.project_name}/\n")
        f.write("├── inputs/           # Input data\n")
        f.write("├── intermediate/     # Processing files\n") 
        f.write("└── outputs/          # Final results\n")
        f.write(f"    └── tutorial_analysis_{timestamp}/\n")
        f.write("        ├── rasters/  # Geospatial outputs\n")
        f.write("        └── reports/  # Documentation\n")
        f.write("```\n\n")
        
        f.write("## Next Steps\n\n")
        f.write("- Modify parameters for your own analysis\n")
        f.write("- Use real geospatial data with coordinate systems\n")
        f.write("- Integrate with other Hazelbean functions\n")
        f.write("- Add visualization and plotting\n")
    
    print(f"✓ Generated report: {os.path.basename(report_file)}")
    
    # Create quick summary for console
    print()
    print("=== Project Summary ===")
    print(f"Project name: {p.project_name}")
    print(f"Project directory: {p.project_dir}")
    print(f"Analysis outputs: {os.path.relpath(analysis_dir, p.project_dir)}")
    
    # Count files in each directory
    for subdir, name in [(rasters_dir, 'Rasters'), (reports_dir, 'Reports')]:
        file_count = len([f for f in os.listdir(subdir) if os.path.isfile(os.path.join(subdir, f))])
        print(f"{name}: {file_count} files")
    
    print()
    print("🎉 Tutorial complete! You've learned:")
    print("  ✓ ProjectFlow setup and directory management")
    print("  ✓ Intelligent file discovery with get_path()")
    print("  ✓ Basic raster processing and transformations")
    print("  ✓ Spatial analysis and multi-raster operations") 
    print("  ✓ Professional result organization and documentation")
    print()
    print(f"📁 Check your results in: {analysis_dir}")
    print("📖 Read the full report for next steps and customization ideas")


if __name__ == "__main__":
    main()
