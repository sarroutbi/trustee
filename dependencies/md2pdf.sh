#!/bin/bash
#
# Markdown to PDF Converter
#
# Converts markdown files to PDF using pandoc with proper Unicode support
# for emoji characters (✅, ❌, etc.).
#
# Usage:
#     ./md2pdf.sh input.md [output.pdf]
#     ./md2pdf.sh input.md              # Creates input.pdf
#     ./md2pdf.sh --all                 # Convert all .md files in current dir
#     ./md2pdf.sh --help                # Show help
#
# Requirements:
#     - pandoc
#     - texlive-scheme-full (or at least texlive with xelatex)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    cat << EOF
Markdown to PDF Converter

USAGE:
    $0 <input.md> [output.pdf]
    $0 --all
    $0 --help

OPTIONS:
    <input.md>          Input markdown file
    [output.pdf]        Output PDF file (optional, defaults to input name)
    --all               Convert all .md files in current directory
    --help, -h          Show this help message

EXAMPLES:
    $0 dependencies-rvps.md
    $0 dependencies-rvps.md my-output.pdf
    $0 --all

FEATURES:
    - Unicode support (handles emoji: ✅ ❌ ⚠️ etc.)
    - Table of contents generation
    - Section numbering
    - Proper margins and formatting
    - Clickable links in PDF

EOF
}

# Function to check dependencies
check_dependencies() {
    if ! command -v pandoc &> /dev/null; then
        echo -e "${RED}Error: pandoc is not installed${NC}"
        echo "Install with: sudo dnf install pandoc"
        exit 1
    fi

    if ! command -v xelatex &> /dev/null; then
        echo -e "${RED}Error: xelatex is not installed${NC}"
        echo "Install with: sudo dnf install texlive-scheme-full"
        exit 1
    fi
}

# Function to convert a single file
convert_file() {
    local input="$1"
    local output="$2"

    # If output not specified, derive from input
    if [ -z "$output" ]; then
        output="${input%.md}.pdf"
    fi

    echo -e "${YELLOW}Converting:${NC} $input → $output"

    # Run pandoc with xelatex for Unicode support
    if pandoc "$input" -o "$output" \
        --pdf-engine=xelatex \
        --toc \
        --number-sections \
        -V geometry:margin=1in \
        -V linkcolor:blue \
        2>&1 | grep -v "^$"; then

        echo -e "${GREEN}✅ Success:${NC} Created $output"

        # Show file size
        size=$(du -h "$output" | cut -f1)
        echo -e "   Size: $size"

        return 0
    else
        echo -e "${RED}❌ Failed:${NC} Error converting $input"
        return 1
    fi
}

# Function to convert all markdown files
convert_all() {
    local count=0
    local success=0
    local failed=0

    echo -e "${YELLOW}Converting all .md files in current directory...${NC}\n"

    for file in *.md; do
        if [ -f "$file" ]; then
            count=$((count + 1))
            if convert_file "$file"; then
                success=$((success + 1))
            else
                failed=$((failed + 1))
            fi
            echo ""
        fi
    done

    if [ $count -eq 0 ]; then
        echo -e "${YELLOW}No .md files found in current directory${NC}"
        exit 0
    fi

    echo -e "${GREEN}Conversion complete:${NC}"
    echo -e "  Total:   $count"
    echo -e "  Success: $success"
    if [ $failed -gt 0 ]; then
        echo -e "  ${RED}Failed:  $failed${NC}"
        exit 1
    fi
}

# Main script logic
main() {
    # Check for help flag
    if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        show_usage
        exit 0
    fi

    # Check dependencies
    check_dependencies

    # Check for --all flag
    if [ "$1" = "--all" ]; then
        convert_all
        exit 0
    fi

    # Check if input file provided
    if [ -z "$1" ]; then
        echo -e "${RED}Error: No input file specified${NC}\n"
        show_usage
        exit 1
    fi

    # Check if input file exists
    if [ ! -f "$1" ]; then
        echo -e "${RED}Error: File '$1' not found${NC}"
        exit 1
    fi

    # Check if input is a markdown file
    if [[ ! "$1" =~ \.md$ ]]; then
        echo -e "${YELLOW}Warning: Input file doesn't have .md extension${NC}"
    fi

    # Convert the file
    convert_file "$1" "$2"
}

# Run main function with all arguments
main "$@"
