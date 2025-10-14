# Building RVPS Using Fedora Packaged Crates

**Approach**: Use system-packaged Rust crates (Option A)
**Follows**: Official Fedora Rust Packaging Guidelines
**Network**: Not required during build
**Date**: 2025-10-15

---

## Overview

This guide shows how to build RVPS using **Fedora's packaged Rust crates** instead of downloading dependencies or vendoring. This approach:

✅ Follows [Fedora Rust Packaging Guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/Rust/)
✅ Uses `%cargo_generate_buildrequires` macro
✅ No vendoring required
✅ No network access needed during build
✅ Suitable for official Fedora submission

---

## Prerequisites

### 1. Verify All Dependencies Are Packaged

We've already verified that **all 21 RVPS dependencies** are available as packaged Fedora crates:

✅ anyhow (1.0.99)
✅ async-trait (0.1.89)
✅ base64 (0.22.1)
✅ cfg-if (1.0.3)
✅ chrono (0.4.41)
✅ clap (4.5.45)
✅ config (0.15.13)
✅ env_logger (0.11.8)
✅ log (0.4.28)
✅ prost (0.13.5)
✅ roxmltree (0.20.0)
✅ serde (1.0.225)
✅ serde_json (1.0.143)
✅ sha2 (0.10.9)
✅ shadow-rs (0.8.1)
✅ sled (0.34.7)
✅ strum (0.27.1)
✅ tempfile (3.21.0)
✅ tokio (1.47.1)
✅ tonic (0.12.3)
✅ tonic-build (0.12.3)

### 2. Required Packages

Install the Fedora Rust packaging tools:

```bash
# Install rust-packaging macros
sudo dnf install rust-packaging

# Verify installation
rpm -q rust-packaging cargo-rpm-macros
```

**Note**: `cargo-rpm-macros` should already be installed on Fedora systems with Rust.

---

## Understanding the Approach

### How It Works

1. **`%cargo_prep`**: Sets up cargo environment to use system crates
2. **`%cargo_generate_buildrequires`**: Scans `Cargo.toml` and automatically generates BuildRequires for all dependencies
3. **`%cargo_build`**: Builds using system crates (no download, no vendoring)
4. **`%cargo_test`**: Runs tests using system crates

### Key Differences from Previous Approach

| Aspect | Previous (Online Download) | New (Fedora Crates) |
|--------|---------------------------|---------------------|
| **Network access** | Required during build | Not required |
| **Dependencies** | Downloaded from crates.io | From Fedora packages |
| **BuildRequires** | rust, cargo, gcc only | rust + all rust-*-devel packages |
| **Copr settings** | Enable network access | Default settings (no network) |
| **Fedora compliance** | Non-standard | Follows guidelines |

---

## Step-by-Step Build Process

### Step 1: Prepare Source Tarball

```bash
# Navigate to your trustee repository
cd /path/to/your/trustee

# Set version
VERSION="0.1.0"

# Create source tarball
git archive --format=tar.gz --prefix=trustee-main/ HEAD -o trustee-${VERSION}.tar.gz

# Verify
ls -lh trustee-${VERSION}.tar.gz
```

### Step 2: Build SRPM with Dynamic BuildRequires

The spec file uses `%generate_buildrequires` to dynamically determine dependencies.

```bash
# Set up RPM build environment
rpmdev-setuptree

# Copy new spec file
cp dependencies/trustee-rvps-fedora-crates.spec ~/rpmbuild/SPECS/trustee-rvps.spec

# Copy source tarball
cp trustee-${VERSION}.tar.gz ~/rpmbuild/SOURCES/

# Build SRPM
cd ~/rpmbuild/SPECS
rpmbuild -bs trustee-rvps.spec
```

**Expected output**:
```
Wrote: ~/rpmbuild/SRPMS/trustee-rvps-0.1.0-1.fc42.src.rpm
```

### Step 3: Test Build Locally with Mock

Mock will handle the dynamic BuildRequires generation:

```bash
# Build in mock (uses Fedora packaged crates)
mock -r fedora-42-x86_64 ~/rpmbuild/SRPMS/trustee-rvps-0.1.0-1.fc42.src.rpm

# Watch the build
tail -f /var/lib/mock/fedora-42-x86_64/result/build.log
```

**What to expect**:

1. **First pass** - mock installs rust-packaging and runs `%generate_buildrequires`
2. **BuildRequires generated** - mock creates list of all needed `rust-*-devel` packages
3. **Second pass** - mock installs all BuildRequires and builds the package
4. **Build completes** - creates `trustee-rvps-0.1.0-1.fc42.x86_64.rpm`

### Step 4: Verify Built Package

```bash
# Check results
ls -lh /var/lib/mock/fedora-42-x86_64/result/

# Inspect RPM contents
rpm -qpl /var/lib/mock/fedora-42-x86_64/result/trustee-rvps-0.1.0-1.fc42.x86_64.rpm

# Check dependencies
rpm -qpR /var/lib/mock/fedora-42-x86_64/result/trustee-rvps-0.1.0-1.fc42.x86_64.rpm
```

**Expected files**:
```
/etc/trustee/rvps.json
/usr/bin/rvps
/usr/bin/rvps-tool
/usr/lib/systemd/system/trustee-rvps.service
/usr/share/doc/trustee-rvps/README.md
/usr/share/licenses/trustee-rvps/LICENSE
/var/lib/trustee/rvps
```

### Step 5: Test Installation

```bash
# Install the built RPM
sudo dnf install /var/lib/mock/fedora-42-x86_64/result/trustee-rvps-0.1.0-1.fc42.x86_64.rpm

# Verify binaries
rvps --version
rvps-tool --version

# Test service
sudo systemctl start trustee-rvps
systemctl status trustee-rvps
sudo ss -tlnp | grep 50003
```

---

## Submitting to Copr

### Important: Copr Configuration

**DO NOT enable network access** - this build doesn't need it!

If you previously enabled network access, you can disable it:

```bash
# Disable network access (not needed with this approach)
copr-cli modify YOUR_USERNAME/trustee-rvps --enable-net off
```

### Submit Build

**Via Web UI**:

1. Go to https://copr.fedorainfracloud.org/coprs/YOUR_USERNAME/trustee-rvps/
2. Click **"Builds"** → **"New Build"**
3. Select **"Upload"** tab
4. Upload: `~/rpmbuild/SRPMS/trustee-rvps-0.1.0-1.fc42.src.rpm`
5. Click **"Build"**

**Via copr-cli**:

```bash
copr-cli build YOUR_USERNAME/trustee-rvps ~/rpmbuild/SRPMS/trustee-rvps-0.1.0-1.fc42.src.rpm
```

### Build Process in Copr

**Expected stages**:

1. ✅ **Installing base dependencies** (~1-2 min)
   - rust-packaging, cargo-rpm-macros, etc.

2. ✅ **Generating BuildRequires** (~1-2 min)
   - Runs `%cargo_generate_buildrequires`
   - Creates list of ~50-100 rust-*-devel packages

3. ✅ **Installing Rust dependencies** (~5-10 min)
   - Installs all rust-*-devel packages from Fedora repos
   - No downloads from crates.io!

4. ✅ **Building RVPS** (~5-10 min)
   - Compiles using system crates
   - Links against Fedora packaged libraries

5. ✅ **Creating RPM** (~1 min)

**Total time**: ~15-25 minutes (similar to online approach, but no crates.io downloads)

---

## Comparison with Previous Approaches

### Previous: Online Download (Current Copr Build)

```spec
%build
cd rvps
cargo build --release --locked
# Downloads from crates.io during build
```

**Pros**: Simple, works reliably
**Cons**: Requires network, non-standard for Fedora

### New: Fedora Packaged Crates (This Guide)

```spec
%build
cd rvps
%cargo_build
# Uses /usr/share/cargo/registry/* (Fedora packages)
```

**Pros**: Follows Fedora guidelines, no network, suitable for official Fedora
**Cons**: More complex spec file, requires all deps to be packaged

---

## Troubleshooting

### Issue 1: BuildRequires Generation Scans Entire Workspace

**Symptom**:
```
Problem 1: nothing provides requested (crate(actix-cors/default) >= 0.7.0...)
Problem 2: nothing provides requested (crate(regorus/default) >= 0.2.6...)
Problem 33: nothing provides requested (crate(x509-parser/default) >= 0.17.0...)
```

**Cause**: The `%cargo_generate_buildrequires` macro is scanning the entire trustee workspace (KBS + AS + RVPS) instead of just the rvps subdirectory. Cargo automatically detects workspace membership and scans all workspace dependencies.

**Impact**: Many KBS and Attestation Service dependencies (like actix-cors, regorus, sev, s390_pv, nvml-wrapper) are NOT packaged in Fedora, causing the build to fail.

**Solution**: Break workspace membership IN `%generate_buildrequires` (not `%prep`!) by removing rvps from the workspace members list:

**CRITICAL**: The sed command MUST be in `%generate_buildrequires`, not `%prep`! RPM execution order is:
1. Extract SRPM
2. Run `%generate_buildrequires` ← Dependencies scanned HERE!
3. Install BuildRequires
4. Run `%prep` ← Too late!

```spec
%prep
%autosetup -n trustee-main
cd rvps
%cargo_prep

%generate_buildrequires
# CRITICAL: sed command MUST be here, BEFORE %cargo_generate_buildrequires!
sed -i '/^[[:space:]]*"rvps"/d' Cargo.toml
cd rvps
%cargo_generate_buildrequires
```

This ensures only RVPS's 21 dependencies are scanned, not the entire workspace.

### Issue 2: BuildRequires Generation Fails

**Symptom**:
```
ERROR: %cargo_generate_buildrequires failed
```

**Cause**: Missing `rust-packaging` or issue with Cargo.toml

**Solution**:
```bash
# Ensure rust-packaging is installed
sudo dnf install rust-packaging

# Verify Cargo.toml is valid
cd rvps
cargo metadata --format-version 1
```

### Issue 2: Missing Rust Crate Package

**Symptom**:
```
Error: No match for: rust-some-crate-devel
```

**Cause**: A dependency is not packaged in Fedora

**Solution**:
1. Check if crate is actually packaged:
   ```bash
   dnf search rust-some-crate
   ```
2. If not found, you may need to:
   - Package it yourself (submit to Fedora)
   - Use vendoring approach instead
   - Find an alternative dependency

### Issue 3: Version Mismatch

**Symptom**:
```
error: failed to select a version for dependency `some-crate`
  required by package `rvps v0.1.0`
  Fedora has: 1.2.0
  Cargo.lock wants: 1.3.0
```

**Cause**: Fedora packaged version is older/newer than Cargo.lock

**Solutions**:
1. **Update Cargo.lock** to accept Fedora's version (preferred):
   ```bash
   cd rvps
   cargo update -p some-crate --precise 1.2.0
   cargo generate-lockfile
   ```

2. **Request newer package** in Fedora (slower)

3. **Fall back to vendoring** for that specific crate

### Issue 4: Build Slower Than Expected

**Symptom**: Build takes 30+ minutes

**Cause**: Many dependencies to compile from Fedora sources

**Solution**: This is normal. Fedora packages provide sources, not pre-compiled binaries.

**Note**: Subsequent builds will be faster due to caching.

---

## Advantages of This Approach

### ✅ Fedora Compliance
- Follows official Rust packaging guidelines
- Suitable for submission to official Fedora repos
- Uses Fedora's recommended macros

### ✅ No Vendoring
- Cleaner source package
- Smaller SRPM size
- No need to maintain vendor tarball

### ✅ No Network Access
- Build is reproducible
- Not affected by crates.io downtime
- Works in isolated build environments

### ✅ Security
- Uses vetted Fedora packages
- Packages are maintained by Fedora community
- Security updates handled by Fedora

### ✅ Consistency
- Same approach as other Fedora Rust packages
- Familiar to Fedora packagers
- Standard tooling

---

## Next Steps

### After Successful Build

1. **Test thoroughly**:
   ```bash
   sudo dnf copr enable YOUR_USERNAME/trustee-rvps
   sudo dnf install trustee-rvps
   sudo systemctl start trustee-rvps
   systemctl status trustee-rvps
   ```

2. **Compare with previous build**:
   - Check binary size
   - Test functionality
   - Verify version output

3. **Consider official Fedora submission**:
   - Package meets guidelines
   - All dependencies available
   - Could be submitted for Fedora review

---

## Files

### New Spec File
- **Location**: `dependencies/trustee-rvps-fedora-crates.spec`
- **Purpose**: Spec file using Fedora packaged crates
- **Key differences**: Uses `%cargo_*` macros, `%generate_buildrequires`

### Previous Spec File (for comparison)
- **Location**: `dependencies/trustee-rvps-no-vendor.spec`
- **Purpose**: Spec file with online downloads
- **Use case**: Fallback if Fedora crates approach has issues

---

## References

- **Fedora Rust Guidelines**: https://docs.fedoraproject.org/en-US/packaging-guidelines/Rust/
- **cargo-rpm-macros**: https://pagure.io/fedora-rust/rust2rpm
- **rust2rpm tool**: https://pagure.io/fedora-rust/rust2rpm
- **Fedora Package Review**: https://fedoraproject.org/wiki/Package_Review_Process

---

**Last Updated**: 2025-10-15
**Approach**: Fedora Packaged Crates (Recommended)
**Compliance**: Fedora Rust Packaging Guidelines v1.0
