#!/bin/bash
# Local build simulation for RVPS package
# Simulates what Copr does during the build

set -e

echo "=========================================="
echo "RVPS Local Build Simulation"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Build directory
BUILD_DIR="/tmp/rvps-local-build"
SOURCE_DIR="/home/sarroutb/RedHat/TASKS/TRUSTEE/github/sarroutbi/trustee"

echo -e "${BLUE}Step 1: Installing build dependencies...${NC}"
echo "Checking if build dependencies are installed..."
DEPS_NEEDED=""

for pkg in rust cargo gcc protobuf-compiler git systemd-rpm-macros; do
    if ! rpm -q $pkg &>/dev/null; then
        DEPS_NEEDED="$DEPS_NEEDED $pkg"
    else
        echo "  ✓ $pkg is installed"
    fi
done

if [ -n "$DEPS_NEEDED" ]; then
    echo -e "${RED}Missing dependencies:$DEPS_NEEDED${NC}"
    echo "Install with: sudo dnf install$DEPS_NEEDED"
    exit 1
fi

echo -e "${GREEN}All build dependencies are installed!${NC}"
echo ""

echo -e "${BLUE}Step 2: Creating build directory...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"
echo "  Build directory: $BUILD_DIR"
echo ""

echo -e "${BLUE}Step 3: Extracting source (simulating SRPM unpack)...${NC}"
# Copy source to build directory (simulating what rpmbuild does)
cp -r "$SOURCE_DIR" "$BUILD_DIR/trustee-main"
cd "$BUILD_DIR/trustee-main"
echo "  Source extracted to: $BUILD_DIR/trustee-main"
echo ""

echo -e "${BLUE}Step 4: Building RVPS (this is what Copr does)...${NC}"
echo "  Changing to rvps directory..."
cd rvps

echo "  Running: cargo build --release --locked"
echo "  This will download and compile Rust dependencies..."
echo "  (This may take 15-20 minutes on first build)"
echo ""

# Capture start time
START_TIME=$(date +%s)

# Run cargo build (same as spec file)
cargo build --release --locked

# Capture end time
END_TIME=$(date +%s)
BUILD_TIME=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}Build completed successfully!${NC}"
echo "  Build time: $BUILD_TIME seconds (~$(($BUILD_TIME / 60)) minutes)"
echo ""

echo -e "${BLUE}Step 5: Verifying binaries...${NC}"
RVPS_BIN="../target/release/rvps"
RVPS_TOOL_BIN="../target/release/rvps-tool"

if [ -f "$RVPS_BIN" ]; then
    SIZE=$(du -h "$RVPS_BIN" | cut -f1)
    echo "  ✓ rvps binary created: $SIZE"
    echo "    Location: $(readlink -f $RVPS_BIN)"
    echo "    Testing binary..."
    $RVPS_BIN --version
else
    echo -e "  ${RED}✗ rvps binary not found!${NC}"
    exit 1
fi

if [ -f "$RVPS_TOOL_BIN" ]; then
    SIZE=$(du -h "$RVPS_TOOL_BIN" | cut -f1)
    echo "  ✓ rvps-tool binary created: $SIZE"
    echo "    Location: $(readlink -f $RVPS_TOOL_BIN)"
    echo "    Testing binary..."
    $RVPS_TOOL_BIN --version
else
    echo -e "  ${RED}✗ rvps-tool binary not found!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Build simulation completed successfully!"
echo "==========================================${NC}"
echo ""
echo "Binaries are located at:"
echo "  - $(readlink -f $RVPS_BIN)"
echo "  - $(readlink -f $RVPS_TOOL_BIN)"
echo ""
echo "To test the binaries:"
echo "  $(readlink -f $RVPS_BIN) --help"
echo "  $(readlink -f $RVPS_TOOL_BIN) --help"
echo ""
echo "To clean up build directory:"
echo "  rm -rf $BUILD_DIR"
echo ""
