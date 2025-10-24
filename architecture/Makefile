# Hazelbean Architecture Diagram Makefile

.PHONY: diagrams clean view help install

# Default target
all: diagrams

# Generate all diagram formats
diagrams:
	@echo "🏗️  Generating Hazelbean architecture diagrams..."
	python generate_diagram.py

# Generate diagrams manually using DOT (if Python script fails)
diagrams-manual:
	@echo "🔧 Generating diagrams manually from DOT file..."
	dot -Tpng hazelbean_architecture.dot -o hazelbean_architecture.png
	dot -Tsvg hazelbean_architecture.dot -o hazelbean_architecture.svg  
	dot -Tpdf hazelbean_architecture.dot -o hazelbean_architecture.pdf
	@echo "✅ Manual generation complete!"

# Clean generated files (keep source files)
clean:
	@echo "🧹 Cleaning generated diagram files..."
	rm -f *.png *.svg *.pdf
	@echo "✅ Clean complete!"

# Open the PNG diagram
view: diagrams
	@echo "👀 Opening architecture diagram..."
	open hazelbean_architecture.png

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	conda install -c conda-forge python-graphviz
	@echo "✅ Dependencies installed!"

# Install for pip users
install-pip:
	@echo "📦 Installing dependencies with pip..."
	@echo "⚠️  Note: You also need system Graphviz: brew install graphviz"
	pip install graphviz
	@echo "✅ Python package installed!"

# Show help
help:
	@echo "Hazelbean Architecture Diagram Generator"
	@echo ""
	@echo "Available targets:"
	@echo "  diagrams        Generate all diagram formats (PNG, SVG, PDF)"
	@echo "  diagrams-manual Generate using DOT command directly"
	@echo "  view            Generate and open PNG diagram" 
	@echo "  clean           Remove generated files"
	@echo "  install         Install conda dependencies"
	@echo "  install-pip     Install pip dependencies"
	@echo "  help            Show this help message"
	@echo ""
	@echo "Files generated:"
	@echo "  hazelbean_architecture.png  - High-res image for presentations"
	@echo "  hazelbean_architecture.svg  - Scalable vector for web docs"
	@echo "  hazelbean_architecture.pdf  - High-quality PDF for printing"
	@echo ""
	@echo "Sprint Focus Areas (highlighted in red):"
	@echo "  • ProjectFlow Management"
	@echo "  • get_path() System (local + cloud)"
	@echo "  • Tiling Iterator" 
	@echo "  • Testing Infrastructure"
