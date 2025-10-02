#!/bin/bash

echo "====================================="
echo "Verifying Exchange Scraper Setup"
echo "====================================="
echo

# Check required files
echo "Checking required files..."
required_files=(
    "exchange_scraper_fixed.py"
    "app/webserver.py"
    "app/scheduler.py"
    "app/comparison.py"
    "app/excel_generator.py"
    "app/static/index.html"
    "Dockerfile"
    "docker-compose.yml"
    "requirements.txt"
    "data/past_results_cache.json"
)

all_present=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (MISSING)"
        all_present=false
    fi
done

echo
echo "Checking directory structure..."
required_dirs=(
    "app"
    "app/static"
    "data"
    "data/output"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✓ $dir/"
    else
        echo "✗ $dir/ (MISSING)"
        all_present=false
    fi
done

echo
echo "Checking Python syntax..."
if python3 -m py_compile exchange_scraper_fixed.py app/*.py 2>/dev/null; then
    echo "✓ All Python files have valid syntax"
else
    echo "✗ Python syntax errors detected"
    all_present=false
fi

echo
echo "====================================="
if [ "$all_present" = true ]; then
    echo "✓ Setup verification PASSED"
    echo
    echo "You can now run:"
    echo "  docker compose up -d"
    echo
    echo "Then access the dashboard at:"
    echo "  http://localhost:9089"
else
    echo "✗ Setup verification FAILED"
    echo "Some files or directories are missing"
fi
echo "====================================="
