# Tutorial Examples: Complete Workflow Progression

Welcome to the Hazelbean tutorial series! This comprehensive learning journey takes you through the entire geospatial processing workflow, from initial project setup to professional result organization.

## Learning Path Overview

!!! tip "Progressive Learning"
    Each step builds on the previous ones. Complete them in order for the best learning experience.

| Step | Topic | Learning Time | Key Concepts |
|------|-------|---------------|---------------|
| **1** | Project Setup | 5 minutes | ProjectFlow, Directory Structure |
| **2** | Data Loading | 10 minutes | get_path(), File Discovery, Raster Info |
| **3** | Processing | 15 minutes | Array Operations, Transformations |
| **4** | Analysis | 20 minutes | Spatial Analysis, Multi-raster Operations |
| **5** | Export Results | 15 minutes | Professional Organization, Documentation |

**Total Learning Time:** ~65 minutes

---

## Step 1: Project Setup

::: examples.step_1_project_setup

!!! success "📚 Learning Objectives"
    **By completing this step, you will:**
    
    - ✅ Initialize a Hazelbean ProjectFlow for organized geospatial workflows
    - ✅ Understand the intelligent directory structure that Hazelbean creates  
    - ✅ Master the data discovery hierarchy and how get_path() searches for files
    - ✅ Build the foundation for all subsequent Hazelbean projects
    
    **Prerequisites:** Basic Python knowledge  
    **Estimated Time:** 5 minutes  
    **Difficulty:** 🟢 Beginner

!!! note "🎯 Key Takeaway"
    **ProjectFlow** is the foundation of every Hazelbean workflow. It creates an organized directory structure and provides intelligent file path resolution that makes your analysis reproducible and professional. Think of it as your "project manager" that keeps everything organized automatically.

!!! example "💡 Real-World Application"
    In research and professional work, you'll often work with multiple datasets across different projects. ProjectFlow ensures that your analysis remains organized and reproducible, whether you're analyzing land cover changes, environmental impact assessments, or climate modeling.

---

## Step 2: Data Loading

::: examples.step_2_data_loading

!!! success "📚 Learning Objectives"
    **By completing this step, you will:**
    
    - ✅ Master Hazelbean's intelligent file discovery system with get_path()
    - ✅ Load and examine geospatial raster data efficiently
    - ✅ Understand raster metadata and properties for analysis planning
    - ✅ Handle missing data scenarios gracefully with fallback patterns
    
    **Prerequisites:** Completed Step 1 (Project Setup)  
    **Estimated Time:** 10 minutes  
    **Difficulty:** 🟡 Intermediate

!!! tip "💡 Pro Insight"
    **get_path()** is Hazelbean's "smart search engine" for your files. It searches through multiple data directories automatically, following a intelligent hierarchy:
    
    1. Project-specific directories first
    2. Base data directories 
    3. Model-wide data repositories
    4. Current working directory as fallback
    
    This means your code works whether data is local to your project, shared across projects, or in a centralized data repository.

---

## Step 3: Processing

::: examples.step_3_basic_processing

!!! success "📚 Learning Objectives"
    **By completing this step, you will:**
    
    - ✅ Apply mathematical operations to raster data efficiently
    - ✅ Perform coordinate transformations between spatial reference systems
    - ✅ Create derived datasets through raster calculations
    - ✅ Handle different data types and scaling factors appropriately
    
    **Prerequisites:** Completed Steps 1-2 (Setup & Data Loading)  
    **Estimated Time:** 15 minutes  
    **Difficulty:** 🟡 Intermediate

!!! warning "🎯 Critical Concept"
    **Spatial Reference Systems (CRS)** are fundamental to geospatial analysis:
    
    - **Always verify** your coordinate reference systems when combining datasets
    - **Different CRS** can make data appear misaligned even when geographically correct
    - **Hazelbean helps** with transformations, but understanding your data's spatial properties prevents analysis errors
    - **Rule of thumb:** Match all datasets to the same CRS before analysis

!!! info "🔧 Technical Deep Dive" 
    Raster processing involves working with **multi-dimensional arrays** where each cell represents a geographic location. Understanding data types (float32 vs int16), no-data values, and scaling factors ensures your mathematical operations produce meaningful results.

---

## Step 4: Analysis

::: examples.step_4_analysis

!!! success "📚 Learning Objectives"
    **By completing this step, you will:**
    
    - ✅ Combine multiple raster datasets in sophisticated spatial analysis
    - ✅ Perform zonal statistics and regional summaries for insights
    - ✅ Create classification maps and derived analytical products
    - ✅ Handle complex analytical workflows efficiently and reproducibly
    
    **Prerequisites:** Completed Steps 1-3 (Setup, Data Loading, Basic Processing)  
    **Estimated Time:** 20 minutes  
    **Difficulty:** 🟠 Advanced

!!! example "🌍 Real-World Applications"
    **This step demonstrates patterns you'll use for:**
    
    - **🌳 Land Cover Analysis:** Classify land use types and track changes over time
    - **📈 Change Detection:** Compare datasets across different time periods  
    - **🌊 Environmental Impact:** Assess how human activities affect natural systems
    - **🎯 Regional Planning:** Analyze patterns within administrative or ecological boundaries
    - **📊 Resource Management:** Quantify natural resources within specific regions

!!! note "🧮 Analysis Philosophy"
    **Multi-raster operations** represent the core of spatial analysis. You're not just processing individual datasets, but discovering **relationships and patterns** that emerge when data sources are combined intelligently.

---

## Step 5: Export Results

::: examples.step_5_export_results

!!! success "📚 Learning Objectives"
    **By completing this step, you will:**
    
    - ✅ Organize analysis outputs in professional directory structures
    - ✅ Create comprehensive documentation and metadata for reproducibility
    - ✅ Generate detailed analysis reports with clear summaries and insights
    - ✅ Establish reproducible workflows for sharing and collaboration
    
    **Prerequisites:** Completed Steps 1-4 (Complete analysis workflow)  
    **Estimated Time:** 15 minutes  
    **Difficulty:** 🟢 Beginner (concepts) / 🟠 Advanced (best practices)

!!! quote "💼 Professional Best Practice"
    **Documentation and organization** are just as important as the analysis itself. Well-organized results with clear documentation:
    
    - **Enable collaboration** with colleagues and stakeholders
    - **Ensure reproducibility** for future research and validation  
    - **Facilitate peer review** and publication processes
    - **Save time** when you return to a project months later
    - **Build credibility** in professional and academic settings

!!! tip "🎯 Career Impact"
    **Professional result organization distinguishes expert practitioners:**
    
    - **Junior level:** Focuses on getting the analysis to work
    - **Intermediate level:** Produces clean code and basic documentation  
    - **Expert level:** Creates comprehensive, self-documenting workflows that others can build upon
    
    This step teaches **expert-level practices** that make your work valuable beyond the immediate analysis.

---

## Quick Start Guide

!!! abstract "Ready to Begin?"
    
    **Prerequisites:**
    - Python environment with Hazelbean installed
    - Basic familiarity with Python programming
    - Understanding of geospatial data concepts (helpful but not required)

    **Setup Instructions:**
    
    === "macOS"
        ```bash
        # Activate your environment
        conda activate hazelbean_env
        
        # Navigate to examples directory
        cd hazelbean_dev/examples/
        
        # Run the first tutorial
        python step_1_project_setup.py
        
        # Alternative: Run from anywhere with full path
        python ~/path/to/hazelbean_dev/examples/step_1_project_setup.py
        ```
    
    === "Windows"
        ```cmd
        REM Activate your environment
        conda activate hazelbean_env
        
        REM Navigate to examples directory
        cd hazelbean_dev\examples\
        
        REM Run the first tutorial  
        python step_1_project_setup.py
        
        REM Alternative: Run from anywhere with full path
        python C:\path\to\hazelbean_dev\examples\step_1_project_setup.py
        ```
    
    === "Linux"
        ```bash
        # Activate your environment
        conda activate hazelbean_env
        
        # Navigate to examples directory
        cd hazelbean_dev/examples/
        
        # Run the first tutorial
        python step_1_project_setup.py
        
        # Alternative: Make executable and run directly
        chmod +x step_1_project_setup.py
        ./step_1_project_setup.py
        ```

## Learning Support

!!! question "Need Help?"
    
    - **Got stuck?** Each example includes error handling and fallback options
    - **Want more detail?** Check the comprehensive docstrings in each function
    - **Ready for more?** Explore the [Test Documentation](../tests/index.md) for advanced patterns
    - **Have questions?** Review the source code directly in the examples/ directory

!!! info "Next Steps"
    After completing this tutorial series, you'll be ready to:
    
    - Build your own geospatial analysis workflows
    - Integrate Hazelbean with other geospatial libraries
    - Contribute to the Hazelbean project
    - Explore advanced features in the full documentation

---

*This educational content is automatically extracted from the latest example code, ensuring it stays up-to-date with current best practices.*
