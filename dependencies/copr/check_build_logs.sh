#!/bin/bash
# Script to check Copr build logs for trustee-rvps
# Usage: ./check_build_logs.sh BUILD_ID
# Example: ./check_build_logs.sh 9691202

if [ -z "$1" ]; then
    echo "Usage: $0 BUILD_ID"
    echo "Example: $0 9691202"
    exit 1
fi

BUILDID="$1"
# Add leading zero if needed (Copr uses 8-digit format)
BUILDID_PADDED=$(printf "%08d" "$BUILDID")

BASE_URL="https://download.copr.fedorainfracloud.org/results/sarroutb/trustee-rvps/fedora-42-x86_64/${BUILDID_PADDED}-trustee-rvps"
LOG_URL="${BASE_URL}/builder-live.log.gz"

echo "============================================"
echo "Checking build: $BUILDID_PADDED"
echo "URL: $LOG_URL"
echo "============================================"
echo ""

# Check if log exists
if ! curl -sf "$LOG_URL" > /dev/null; then
    echo "ERROR: Build log not found at $LOG_URL"
    echo ""
    echo "Possible reasons:"
    echo "1. Build ID is incorrect"
    echo "2. Build hasn't started yet"
    echo "3. Build is still running"
    echo ""
    echo "Try visiting: https://copr.fedorainfracloud.org/coprs/sarroutb/trustee-rvps/builds/"
    exit 1
fi

echo "✓ Log file found, downloading and analyzing..."
echo ""

# Download log once
LOGFILE="/tmp/build-${BUILDID_PADDED}.log"
curl -sL "$LOG_URL" | gunzip > "$LOGFILE"

echo "============================================"
echo "1. Checking %generate_buildrequires execution"
echo "============================================"
grep -A 30 "Executing.*generate_buildrequires" "$LOGFILE" | head -35
echo ""

echo "============================================"
echo "2. Checking for workspace inheritance errors"
echo "============================================"
if grep -q "error inheriting" "$LOGFILE"; then
    echo "❌ FOUND workspace inheritance errors:"
    grep "error inheriting" "$LOGFILE"
else
    echo "✓ No workspace inheritance errors"
fi
echo ""

echo "============================================"
echo "3. Checking for KBS/AS dependencies (should be 0)"
echo "============================================"
ACTIX_COUNT=$(grep -c "actix-cors" "$LOGFILE" || true)
REGORUS_COUNT=$(grep -c "regorus" "$LOGFILE" || true)
SEV_COUNT=$(grep -c "crate(sev" "$LOGFILE" || true)

echo "actix-cors mentions: $ACTIX_COUNT (should be 0)"
echo "regorus mentions: $REGORUS_COUNT (should be 0)"
echo "sev mentions: $SEV_COUNT (should be 0)"

if [ "$ACTIX_COUNT" -eq 0 ] && [ "$REGORUS_COUNT" -eq 0 ] && [ "$SEV_COUNT" -eq 0 ]; then
    echo "✓ No KBS/AS dependencies found - workspace isolation working!"
else
    echo "❌ Still finding workspace dependencies - fix not working yet"
fi
echo ""

echo "============================================"
echo "4. Checking for dependency resolution problems"
echo "============================================"
PROBLEM_COUNT=$(grep -c "^Problem [0-9]*:" "$LOGFILE" || true)
echo "Total dependency problems: $PROBLEM_COUNT"

if [ "$PROBLEM_COUNT" -gt 0 ]; then
    echo ""
    echo "First 10 problems:"
    grep "^Problem [0-9]*:" "$LOGFILE" | head -10
else
    echo "✓ No dependency problems!"
fi
echo ""

echo "============================================"
echo "5. Checking build outcome"
echo "============================================"
if grep -q "Finish: build phase for" "$LOGFILE"; then
    echo "✓ Build phase completed"
    if grep -q "Finish: rpmbuild trustee-rvps.*src.rpm" "$LOGFILE"; then
        echo "✓ SRPM build succeeded"
    fi
    if grep -q "Wrote:.*trustee-rvps.*x86_64.rpm" "$LOGFILE"; then
        echo "✓ Binary RPM created - BUILD SUCCESSFUL!"
    elif grep -q "ERROR:" "$LOGFILE"; then
        echo "❌ Build failed with errors"
        echo ""
        echo "Last 20 lines of log:"
        tail -20 "$LOGFILE"
    fi
else
    echo "Build still in progress or failed early"
    echo ""
    echo "Last 30 lines of log:"
    tail -30 "$LOGFILE"
fi
echo ""

echo "============================================"
echo "Full log saved to: $LOGFILE"
echo "============================================"
