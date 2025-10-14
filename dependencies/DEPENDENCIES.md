# Trustee Dependencies Documentation

This directory contains comprehensive dependency analysis and verification tools for packaging Trustee components as RPMs for Fedora and RHEL distributions.

## Contents

### 📄 Documentation Files

#### 1. `dependencies-analysis.md`
**Purpose:** General dependency analysis covering all Trustee components (KBS, Attestation Service, RVPS)

**Target Distributions:** Fedora 42 and RHEL 10.2

**Key Sections:**
- Build and runtime dependencies for all components
- System library requirements
- Proposed installation layouts (FHS-compliant)
- Feature flags and build variants
- Risk assessment and mitigation strategies
- Packaging recommendations
- Example RPM spec snippets

**When to use:** Reference this document when planning overall Trustee packaging strategy or understanding dependencies across all components.

---

#### 2. `dependencies-rvps.md`
**Purpose:** Detailed RVPS-specific packaging analysis

**Focus:** Reference Value Provider Service (RVPS) standalone packaging

**Key Sections:**
- RVPS component overview and architecture
- Minimal build dependencies (no OpenSSL required!)
- Runtime dependencies (glibc only)
- Feature flag analysis
- Complete systemd service configuration
- Security hardening recommendations
- Example RPM spec file
- Integration guide with Attestation Service

**When to use:** Reference this when packaging RVPS component separately. RVPS is the simplest component to package (fewer dependencies, no OpenSSL).

**Highlights:**
- ✅ No OpenSSL dependency (pure Rust)
- ✅ ~30-40 crates (vs 200+ for KBS)
- ✅ Smaller binary size (~10 MB)
- ✅ Architecture-agnostic

---

#### 3. `rhel-10.2-verification.md`
**Purpose:** RHEL 10.2 Beta verification results

**System Tested:** RHEL 10.2 Beta (Coughlan) at 10.0.184.129

**Key Findings:**
- ✅ All dependencies VERIFIED and AVAILABLE
- ✅ Protobuf compiler: identical version 3.19.6 (same as Fedora 42)
- ✅ Rust 1.89.0 (excellent version)
- ✅ OpenSSL 3.5.1 (newer than Fedora!)
- ✅ NO BLOCKERS for RHEL 10.2 packaging

**When to use:** Reference this to confirm RHEL 10.2 compatibility or when updating dependency tables with verified versions.

---

### 🔧 Verification Tools

#### 4. `check-fedora-packages.py`
**Purpose:** Automated package availability checker for Fedora repositories

**What it does:**
- Parses dependency markdown files
- Queries https://src.fedoraproject.org/rpms/ for each package
- Verifies package existence in Fedora
- Generates detailed verification report

**Usage:**

```bash
# Basic check on RVPS dependencies
./check-fedora-packages.py dependencies-rvps.md

# Verbose mode (shows package URLs)
./check-fedora-packages.py dependencies-rvps.md --verbose

# Check general analysis file
./check-fedora-packages.py dependencies-analysis.md -v

# Help
./check-fedora-packages.py --help
```

**Output Format:**

```
Checking 8 packages in Fedora repositories...

✅ FOUND      rust                      (Fedora: 1.90.0)
✅ FOUND      cargo                     (Fedora: 1.90.0)
✅ FOUND      gcc                       (Fedora: 15.2.1)
✅ FOUND      protobuf-compiler         (Fedora: 3.19.6)
❌ NOT FOUND  example-missing-pkg       (Fedora: 1.0.0)

================================================================================
VERIFICATION SUMMARY
================================================================================

BUILD DEPENDENCIES:
  Found:     7
  Not Found: 1

  Missing BUILD packages:
    - example-missing-pkg (required: >= 1.0)

TOTAL: 7/8 packages found in Fedora

⚠️  WARNING: 1 package(s) not found in Fedora repositories
```

**Exit Codes:**
- `0`: All packages found (success)
- `1`: One or more packages not found or error

**Requirements:**
- Python 3.6+
- `requests` library: `pip install requests`

**Key Features:**
- **Automatic source package mapping:** The script automatically maps binary package names (e.g., `protobuf-compiler`, `libgcc`) to their source package names (e.g., `protobuf`, `gcc`) since src.fedoraproject.org uses source package names.
- **Markdown table parsing:** Automatically extracts packages from dependency tables
- **HTTP verification:** Queries actual Fedora repositories to confirm package existence
- **Detailed reporting:** Shows found/missing packages with clear status indicators

**When to use:**
- Verify dependency tables are accurate
- Double-check package names before creating spec files
- Automate CI/CD dependency validation
- Cross-reference with actual Fedora package database

---

#### 5. `check-rhel-packages.py`
**Purpose:** Automated package availability checker for RHEL 10.2 repositories

**What it does:**
- Parses dependency markdown files
- SSH into RHEL 10.2 system and queries `dnf` for each package
- Verifies package existence and version in RHEL 10.2
- Generates detailed verification report

**Usage:**

```bash
# Basic check on RVPS dependencies (--host is required)
./check-rhel-packages.py dependencies-rvps.md --host 10.0.184.129

# Verbose mode (shows verified versions from dnf)
./check-rhel-packages.py dependencies-rvps.md --host 10.0.184.129 --verbose

# Specify different SSH user
./check-rhel-packages.py dependencies-rvps.md --host 10.0.184.129 --user myuser -v

# Check general analysis file
./check-rhel-packages.py dependencies-analysis.md --host 10.0.184.129 -v

# Help
./check-rhel-packages.py --help
```

**Output Format:**

```
Checking 9 packages on RHEL system 10.0.184.129...

✅ FOUND      rust                      (RHEL: 1.89.0)
✅ FOUND      cargo                     (RHEL: 1.89.0)
✅ FOUND      gcc                       (RHEL: 14.3.1)
❌ NOT FOUND  example-missing-pkg       (RHEL: 1.0.0)

================================================================================
VERIFICATION SUMMARY
================================================================================

BUILD DEPENDENCIES:
  Found:     3
  Not Found: 1

  Missing BUILD packages:
    - example-missing-pkg (required: >= 1.0)

TOTAL: 3/4 packages found in RHEL 10.2

⚠️  WARNING: 1 package(s) not found in RHEL 10.2 repositories
```

**Exit Codes:**
- `0`: All packages found (success)
- `1`: One or more packages not found or error

**Requirements:**
- Python 3.6+
- SSH access to RHEL 10.2 system
- SSH key-based authentication configured (passwordless)

**Key Features:**
- **SSH-based verification:** Directly queries dnf on actual RHEL 10.2 system
- **Real version detection:** Extracts actual package versions from dnf output
- **Package alias mapping:** Automatically handles package name aliases (e.g., pkg-config → pkgconf)
- **Fallback checks:** Tries both --available and --installed package repositories

**When to use:**
- Verify RHEL 10.2 compatibility before packaging
- Cross-check documented versions against actual RHEL repositories
- Automate RHEL dependency validation in CI/CD
- Confirm packages are available on specific RHEL test systems

---

## Converting Documentation to PDF

All markdown files in this directory can be converted to PDF for easier sharing and offline reading.

### Easiest Method: md2pdf.sh script

A convenience script is provided for easy PDF generation:

**Usage:**
```bash
# Convert single file
./md2pdf.sh dependencies-rvps.md

# Convert with custom output name
./md2pdf.sh dependencies-rvps.md my-analysis.pdf

# Convert all markdown files in current directory
./md2pdf.sh --all

# Show help
./md2pdf.sh --help
```

**Features:**
- ✅ Automatically uses xelatex for Unicode emoji support
- ✅ Generates table of contents
- ✅ Section numbering
- ✅ Proper margins and formatting
- ✅ Color output with status indicators
- ✅ Error checking and helpful messages

**Requirements:**
- `pandoc` - Install with: `sudo dnf install pandoc`
- `texlive-scheme-full` - Install with: `sudo dnf install texlive-scheme-full`

### Manual Method: pandoc command-line

**Installation (Fedora/RHEL):**
```bash
# Option 1: Full texlive (recommended, ~2-3 GB, includes all packages)
sudo dnf install pandoc texlive-scheme-full

# Option 2: Minimal install (smaller, but may require additional packages)
sudo dnf install pandoc texlive-scheme-medium \
  texlive-collection-fontsrecommended
```

**Note:** If you get LaTeX errors about missing `.sty` files (like `footnote.sty`), install the full scheme:
```bash
sudo dnf install texlive-scheme-full
```

**Convert single file:**
```bash
# Basic conversion (use xelatex for Unicode support - emoji characters)
pandoc dependencies-rvps.md -o dependencies-rvps.pdf \
  --pdf-engine=xelatex

# With table of contents and better formatting
pandoc dependencies-rvps.md -o dependencies-rvps.pdf \
  --pdf-engine=xelatex \
  --toc \
  --number-sections \
  -V geometry:margin=1in \
  -V linkcolor:blue

# Convert all markdown files
for file in *.md; do
  pandoc "$file" -o "${file%.md}.pdf" \
    --pdf-engine=xelatex \
    --toc \
    --number-sections \
    -V geometry:margin=1in \
    -V linkcolor:blue
done
```

**Important:** These markdown files contain Unicode emoji characters (✅, ❌, etc.) in tables, so you **must** use `--pdf-engine=xelatex` or `--pdf-engine=lualatex`. The default pdflatex engine doesn't support Unicode.

### Alternative Method: grip (GitHub-style rendering)

**Installation:**
```bash
pip install grip
```

**Usage:**
```bash
# Preview in browser (GitHub-style)
grip dependencies-rvps.md

# Export to HTML, then print to PDF from browser
grip dependencies-rvps.md --export dependencies-rvps.html
# Open in browser and use Print → Save as PDF
```

### Alternative Method: markdown-pdf (Node.js)

**Installation:**
```bash
npm install -g markdown-pdf
```

**Usage:**
```bash
# Convert single file
markdown-pdf dependencies-rvps.md

# Convert all markdown files
markdown-pdf *.md
```

### Recommended Pandoc Options Explained

- `--pdf-engine=xelatex` - Use XeLaTeX for Unicode support (**required** for emoji)
- `--toc` - Generate table of contents
- `--number-sections` - Add section numbering (1, 1.1, 1.2, etc.)
- `-V geometry:margin=1in` - Set 1-inch margins
- `-V linkcolor:blue` - Make hyperlinks blue (visible in PDF)
- `--toc-depth=N` - Set TOC depth (default: 3)
- `--metadata title="..."` - Set PDF title metadata

### Example: Convert RVPS documentation

```bash
pandoc dependencies-rvps.md -o dependencies-rvps.pdf \
  --pdf-engine=xelatex \
  --toc \
  --toc-depth=3 \
  --number-sections \
  -V geometry:margin=1in \
  -V linkcolor:blue \
  -V documentclass:report \
  --metadata title="RVPS Packaging Analysis" \
  --metadata author="sarroutbi" \
  --metadata date="2025-10-14"
```

---

## Quick Start Guide

### For First-Time Packagers

1. **Start with RVPS** (easiest component):
   ```bash
   # Read RVPS-specific analysis
   cat dependencies-rvps.md

   # Verify all packages exist in Fedora
   ./check-fedora-packages.py dependencies-rvps.md

   # Verify all packages exist in RHEL 10.2
   ./check-rhel-packages.py dependencies-rvps.md --host 10.0.184.129
   ```

2. **Review RHEL compatibility**:
   ```bash
   cat rhel-10.2-verification.md
   ```

3. **Consult general analysis** for overall strategy:
   ```bash
   cat dependencies-analysis.md
   ```

### For Experienced Packagers

1. **Extract package lists** directly from tables in markdown files
2. **Use verification script** to confirm package availability
3. **Reference spec snippets** in the documentation
4. **Adapt systemd service files** from the examples

---

## Package Dependency Summary

### Build Dependencies (Common)

| Package                | Min Version | Fedora 42 | RHEL 10.2 | Notes                    |
| ---------------------- | ----------- | --------- | --------- | ------------------------ |
| `rust`                 | >= 1.70     | 1.90.0    | 1.89.0    | Compiler                 |
| `cargo`                | >= 1.70     | 1.90.0    | 1.89.0    | Build tool               |
| `gcc`                  | >= 7.0      | 15.2.1    | 14.3.1    | C compiler               |
| `make`                 | Any         | 4.4.1     | ✅        | Build orchestration      |
| `protobuf-compiler`    | >= 3.15     | 3.19.6    | 3.19.6    | gRPC code generation     |
| `git`                  | Any         | 2.51.0    | ✅        | Build metadata           |
| `openssl-devel`        | >= 3.0      | 3.2.6     | ✅        | KBS/AS only (not RVPS)   |
| `pkg-config`           | Any         | ✅        | ✅        | Library detection        |

### Runtime Dependencies (Common)

| Package                | Min Version | Fedora 42 | RHEL 10.2 | Notes                    |
| ---------------------- | ----------- | --------- | --------- | ------------------------ |
| `glibc`                | >= 2.31     | 2.41      | 2.39      | C library                |
| `libgcc`               | >= 7.0      | 15.2.1    | 14.3.1    | GCC runtime              |
| `openssl-libs`         | >= 3.0      | 3.2.6     | 3.5.1     | KBS/AS only (not RVPS)   |

### Component-Specific Notes

**RVPS:**
- ✅ Does NOT require `openssl-devel` at build time
- ✅ Does NOT require `openssl-libs` at runtime
- ✅ Pure Rust implementation
- ✅ Minimal dependencies

**KBS (Key Broker Service):**
- Requires OpenSSL (build and runtime)
- ~200+ Rust crates to vendor
- Multiple feature flag combinations
- Most complex component

**Attestation Service:**
- Requires OpenSSL (build and runtime)
- ~80-100 Rust crates to vendor
- Architecture-specific verifiers

---

## Packaging Recommendations

### Priority Order

1. **RVPS** - Start here (simplest)
2. **Attestation Service** - Medium complexity
3. **KBS** - Most complex (many features)

### Build Process Overview

```bash
# 1. Vendor Rust dependencies (REQUIRED for Fedora/RHEL packaging)
cargo vendor

# 2. Build RVPS
cd rvps
cargo build --release --locked --offline

# 3. Build Attestation Service
cd ../attestation-service
cargo build --release --locked --offline --features grpc-bin,all-verifier,rvps-grpc

# 4. Build KBS
cd ../kbs
make background-check-kbs AS_TYPE=coco-as COCO_AS_INTEGRATION_TYPE=builtin
```

### Key Considerations

1. **Vendoring Required:**
   - All Rust dependencies MUST be vendored
   - Network access not allowed during Fedora/RHEL builds
   - Use `cargo vendor` to create vendor tarball

2. **Feature Flags:**
   - Choose appropriate feature combinations
   - Document enabled features in spec file
   - Test with `--locked --offline` to simulate build environment

3. **Cross-Distribution Compatibility:**
   - Build on RHEL 10.2 for maximum glibc compatibility
   - Or conditionally compile based on glibc version
   - Test binaries on both Fedora 42 and RHEL 10.2

4. **Security:**
   - Create dedicated `trustee` system user
   - Use systemd hardening options
   - Set proper SELinux contexts

---

## Testing Workflow

### 1. Verify Dependencies

```bash
# Check RVPS dependencies in Fedora
./check-fedora-packages.py dependencies-rvps.md

# Check RVPS dependencies in RHEL 10.2
./check-rhel-packages.py dependencies-rvps.md --host 10.0.184.129

# Check overall dependencies in Fedora (verbose)
./check-fedora-packages.py dependencies-analysis.md -v

# Check overall dependencies in RHEL 10.2 (verbose)
./check-rhel-packages.py dependencies-analysis.md --host 10.0.184.129 -v
```

### 2. Build in Mock (Fedora)

```bash
# Create SRPM with vendored dependencies
# Build in mock environment
mock -r fedora-42-x86_64 rebuild trustee-rvps-0.1.0-1.fc42.src.rpm
```

### 3. Test on RHEL 10.2

```bash
# Transfer RPM to RHEL 10.2 system
scp trustee-rvps-*.rpm root@10.0.184.129:/tmp/

# Install and test
ssh root@10.0.184.129 'dnf install -y /tmp/trustee-rvps-*.rpm'
ssh root@10.0.184.129 'systemctl start trustee-rvps'
ssh root@10.0.184.129 'systemctl status trustee-rvps'
```

### 4. Verify Functionality

```bash
# Check service is listening
ssh root@10.0.184.129 'ss -tlnp | grep 50003'

# Test with rvps-tool
ssh root@10.0.184.129 'rvps-tool --help'
```

---

## Updating This Documentation

When package versions change or new dependencies are added:

1. **Update markdown tables** in `dependencies-analysis.md` or `dependencies-rvps.md`
2. **Run verification script** to confirm package availability:
   ```bash
   ./check-fedora-packages.py dependencies-rvps.md
   ```
3. **Update RHEL verification** if testing on new RHEL system:
   ```bash
   ssh root@10.0.184.129 "dnf info --available rust cargo protobuf-compiler"
   ```
4. **Document changes** in the Changelog section of each file

---

## Common Issues and Solutions

### Issue: Package Not Found in Fedora

**Symptom:**
```
❌ NOT FOUND  some-package  (Fedora: 1.2.3)
```

**Solutions:**
1. Check package name spelling
2. Verify package exists: https://src.fedoraproject.org/rpms/
3. Package might be in different repository (updates, testing)
4. Consider bundling if not available

### Issue: Version Mismatch

**Symptom:** Fedora has older version than required

**Solutions:**
1. Check if older version is actually compatible
2. Request version update in Fedora
3. Adjust minimum version requirement if possible
4. Bundle specific version (not recommended)

### Issue: Vendoring Fails

**Symptom:** `cargo vendor` errors or incomplete

**Solutions:**
1. Ensure `Cargo.lock` exists: `cargo generate-lockfile`
2. Update dependencies: `cargo update`
3. Check for git dependencies (need special handling)
4. Verify network connectivity

---

## Additional Resources

### Fedora Packaging

- **Rust Guidelines:** https://docs.fedoraproject.org/en-US/packaging-guidelines/Rust/
- **Package Search:** https://src.fedoraproject.org/
- **Koji Build System:** https://koji.fedoraproject.org/

### RHEL Packaging

- **RHEL 10 Documentation:** https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/10-beta
- **CentOS Stream:** https://www.centos.org/centos-stream/

### Trustee Project

- **Upstream Repository:** https://github.com/confidential-containers/trustee
- **Documentation:** https://github.com/confidential-containers/documentation
- **Confidential Containers:** https://confidentialcontainers.org/

### Related Projects

- **Guest Components:** https://github.com/confidential-containers/guest-components
- **KBS Operator:** https://github.com/confidential-containers/kbs-operator

---

## Changelog

| Date       | Changes                                      |
| ---------- | -------------------------------------------- |
| 2025-10-14 | Initial dependencies documentation index     |
| 2025-10-14 | Added check-rhel-packages.py verification script |
| 2025-10-14 | Added PDF conversion documentation (pandoc) |
| 2025-10-14 | Added md2pdf.sh script for easy PDF generation |

---

**Maintained by:** sarroutbi

**Last Updated:** 2025-10-14
