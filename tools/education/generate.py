#!/usr/bin/env python3
"""
Educational Content Generator for Hazelbean
Simple tool to generate QMD tutorial files from educational examples.

Usage:
    python generate.py                    # Generate all tutorials
    python generate.py --steps 1,2,3     # Generate specific steps  
    python generate.py --dry-run         # Show what would be generated
"""

import os
import sys
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml
from jinja2 import Environment, FileSystemLoader


class EducationalGenerator:
    """Simple educational content generator for Hazelbean tutorials."""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """Initialize generator with educational step configuration."""
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent.parent
        
        # Smart config file resolution
        if not Path(config_path).is_absolute():
            # First try script directory
            script_config = self.script_dir / config_path
            if script_config.exists():
                self.config_path = script_config
            else:
                # Fallback to provided path (relative to current directory)
                self.config_path = Path(config_path)
        else:
            self.config_path = Path(config_path)
        
        # Load configuration
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Setup template environment
        template_dir = Path(__file__).parent / 'templates'
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        
        # Ensure output directory exists (resolve relative to project root)
        output_path = self.config['output']['directory']
        if not Path(output_path).is_absolute():
            self.output_dir = self.project_root / output_path
        else:
            self.output_dir = Path(output_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_tutorials(self, steps: Optional[List[str]] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Generate tutorial QMD files from educational examples."""
        results = {'generated': [], 'skipped': [], 'errors': []}
        steps_config = self.config['educational_steps']
        
        # Filter steps if specified
        if steps:
            steps_config = {k: v for k, v in steps_config.items() if k in steps}
            
        print(f"🎯 Generating educational tutorials...")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"📚 Processing {len(steps_config)} steps")
        
        # Generate individual step tutorials
        for step_id, step_config in steps_config.items():
            try:
                print(f"  Processing {step_id}: {step_config['title']}")
                
                if dry_run:
                    print(f"    [DRY RUN] Would generate {step_id}.qmd")
                    results['generated'].append(step_id)
                    continue
                    
                # Process example file
                processed_content = self.process_example(step_config['file'], step_config)
                if processed_content is None:
                    results['skipped'].append(step_id)
                    continue
                    
                # Generate QMD file  
                qmd_path = self.write_qmd(step_id, step_config, processed_content, steps_config)
                results['generated'].append(step_id)
                print(f"    ✅ Generated: {qmd_path}")
                
            except Exception as e:
                print(f"    ❌ Error processing {step_id}: {e}")
                results['errors'].append({'step': step_id, 'error': str(e)})
        
        # Generate index file if configured
        if self.config['output'].get('include_index', True) and not dry_run:
            try:
                index_path = self.generate_index(steps_config)
                print(f"  ✅ Generated index: {index_path}")
            except Exception as e:
                print(f"  ❌ Error generating index: {e}")
                results['errors'].append({'step': 'index', 'error': str(e)})
                
        return results
    
    def process_example(self, file_path: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract and process content from educational example file."""
        example_path = self.project_root / file_path
        
        if not example_path.exists():
            print(f"    ⚠️ Example file not found: {file_path}")
            return None
            
        # Read source file
        with open(example_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
            
        # Extract docstring and clean code
        docstring_match = re.search(r'"""(.*?)"""', source_code, re.DOTALL)
        docstring = docstring_match.group(1).strip() if docstring_match else ""
        
        # Clean the code for educational presentation
        cleaned_code = self.clean_code_for_tutorial(source_code)
        
        # Generate expected output (simplified)
        expected_output = self.generate_expected_output(config)
        
        # Break code into logical sections
        code_sections = self.extract_code_sections(cleaned_code)
        
        return {
            'source_code': source_code,
            'cleaned_code': cleaned_code,
            'docstring': docstring,
            'expected_output': expected_output,
            'code_sections': code_sections
        }
    
    def clean_code_for_tutorial(self, source_code: str) -> str:
        """Clean source code for educational presentation."""
        lines = source_code.split('\n')
        cleaned_lines = []
        in_main = False
        
        for line in lines:
            # Skip module docstring (already extracted)
            if line.strip().startswith('"""') and not in_main:
                continue
                
            # Start processing from main function
            if 'def main():' in line:
                in_main = True
                continue
                
            # Skip if __name__ == "__main__" block footer
            if line.strip().startswith('if __name__ == "__main__":'):
                break
                
            # Include content inside main function
            if in_main:
                # Remove excessive indentation (4 spaces from function body)
                if line.startswith('    ') and line.strip():
                    cleaned_lines.append(line[4:])
                elif not line.strip():  # Keep blank lines
                    cleaned_lines.append('')
                    
        return '\n'.join(cleaned_lines).strip()
    
    def extract_code_sections(self, code: str) -> List[Dict[str, str]]:
        """Break code into logical sections for step-by-step explanation."""
        sections = []
        current_section = []
        section_title = ""
        
        lines = code.split('\n')
        for line in lines:
            # Detect section boundaries (comments that look like headers)
            if line.strip().startswith('#') and ('===' in line or '---' in line):
                if current_section:
                    sections.append({
                        'title': section_title or 'Code Section',
                        'code': '\n'.join(current_section).strip()
                    })
                    current_section = []
                # Extract title from comment
                section_title = re.sub(r'[#=\-\s]+', ' ', line).strip()
            else:
                current_section.append(line)
                
        # Add final section
        if current_section:
            sections.append({
                'title': section_title or 'Code Section',
                'code': '\n'.join(current_section).strip()
            })
            
        return sections if len(sections) > 1 else []  # Only return if multiple sections
    
    def generate_expected_output(self, config: Dict[str, Any]) -> str:
        """Generate sample expected output for the tutorial."""
        # This is a simplified version - in a real implementation, 
        # you might run the code in a sandbox to capture actual output
        step_examples = {
            'step_1': "=== Hazelbean Project Setup Demo ===\nProject name: hazelbean_tutorial\nProject directory: /path/to/hazelbean_tutorial\n...",
            'step_2': "=== Hazelbean Data Loading Demo ===\n✓ Found raster: /path/to/data/tests/sample.tif\n...",
            'step_3': "=== Basic Processing Operations ===\nProcessing raster data...\n...",
            'step_4': "=== Spatial Analysis Results ===\nAnalysis complete...\n...",
            'step_5': "=== Export Complete ===\nResults saved to outputs/\n..."
        }
        
        # Return example output or generate generic one
        return step_examples.get(config.get('step_id', ''), "Tutorial execution completed successfully.")
    
    def write_qmd(self, step_id: str, step_config: Dict[str, Any], content: Dict[str, Any], 
                  all_steps: Dict[str, Any]) -> Path:
        """Write QMD file using template system."""
        template = self.jinja_env.get_template('step_template.qmd.j2')
        
        # Prepare template context
        context = {
            'step_id': step_id,
            'step': step_config,
            'steps': all_steps,
            'generated_at': datetime.now(),
            'cleaned_code': content['cleaned_code'],
            'expected_output': content['expected_output'],
            'code_sections': content['code_sections']
        }
        
        # Render template
        rendered_content = template.render(**context)
        
        # Write to file
        output_path = self.output_dir / f"{step_id}.qmd"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_content)
            
        return output_path
    
    def generate_index(self, steps: Dict[str, Any]) -> Path:
        """Generate index QMD file for learning path overview."""
        template = self.jinja_env.get_template('index_template.qmd.j2')
        
        context = {
            'steps': steps,
            'generated_at': datetime.now()
        }
        
        rendered_content = template.render(**context)
        
        index_path = self.output_dir / 'index.qmd'
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(rendered_content)
            
        return index_path


def main():
    """Command-line interface for educational content generator."""
    parser = argparse.ArgumentParser(description='Generate educational QMD tutorials from Hazelbean examples')
    parser.add_argument('--steps', help='Comma-separated list of steps to generate (e.g., step_1,step_2)')
    parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be generated without creating files')
    parser.add_argument('--output', help='Override output directory')
    
    args = parser.parse_args()
    
    try:
        # Initialize generator
        generator = EducationalGenerator(args.config)
        
        # Override output directory if specified
        if args.output:
            generator.output_dir = Path(args.output)
            generator.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse steps filter
        steps_filter = None
        if args.steps:
            steps_filter = [s.strip() for s in args.steps.split(',')]
            
        # Generate tutorials
        results = generator.generate_tutorials(steps=steps_filter, dry_run=args.dry_run)
        
        # Report results
        print(f"\n📊 Generation Summary:")
        print(f"  ✅ Generated: {len(results['generated'])} tutorials")
        if results['skipped']:
            print(f"  ⏭️  Skipped: {len(results['skipped'])} tutorials")
        if results['errors']:
            print(f"  ❌ Errors: {len(results['errors'])} tutorials")
            
        if not args.dry_run and results['generated']:
            print(f"\n🎉 Tutorial generation complete!")
            print(f"📁 Output location: {generator.output_dir}")
            
            # Generate relative path for quarto command
            try:
                relative_path = generator.output_dir.relative_to(Path.cwd())
                print(f"🌐 To view:")
                print(f"   1. Activate environment: conda activate hazelbean_env")
                print(f"   2. Render files: cd {relative_path} && quarto render *.qmd")
            except ValueError:
                # If can't make relative path, show absolute
                print(f"🌐 To view:")
                print(f"   1. Activate environment: conda activate hazelbean_env") 
                print(f"   2. Render files: cd {generator.output_dir} && quarto render *.qmd")
            
    except Exception as e:
        print(f"❌ Generator failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
