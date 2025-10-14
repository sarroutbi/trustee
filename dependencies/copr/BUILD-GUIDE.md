# Building RVPS in Copr - Complete Guide

**Target:** Build RVPS package in Copr for Fedora 42
**Repository:** https://copr.fedorainfracloud.org/coprs/YOUR_USERNAME/trustee-rvps/
**Approach:** Online dependency resolution (Cargo downloads dependencies during build)
**Date:** 2025-10-15

---

## Overview

This guide shows how to build the RVPS (Reference Value Provider Service) component in Copr. The build uses Cargo's online dependency resolution, allowing Cargo to download and compile Rust dependencies during the build process.

---

## Prerequisites

### 1. System Dependencies Verified

All required system packages are available in Fedora 42:

```bash
# Verification (already performed):
cd /path/to/your/trustee/dependencies
python3 check-fedora-packages.py dependencies-rvps.md
```

**Result**: 9/9 packages found in Fedora 42
- rust 1.90.0
- cargo 1.90.0
- gcc 15.2.1
- protobuf-compiler 3.19.6
- make 4.4.1
- git 2.51.0
- glibc 2.41
- libgcc 15.2.1
- golang (optional, for in-toto feature)

### 2. Copr Account and Project

Required setup:
- Copr account: Your username (e.g., `YOUR_USERNAME`)
- Copr project: `trustee-rvps`
- Project URL: https://copr.fedorainfracloud.org/coprs/YOUR_USERNAME/trustee-rvps/

If you don't have a project yet:
```bash
# Create Copr project
copr-cli create trustee-rvps \
  --chroot fedora-42-x86_64 \
  --description "RVPS (Reference Value Provider Service) for Trustee - Confidential Computing attestation" \
  --instructions "https://github.com/confidential-containers/trustee"
```

Or create it via the web UI at: https://copr.fedorainfracloud.org/

---

## Step 1: Enable Network Access in Copr Project

**CRITICAL**: Cargo needs to download dependencies from crates.io during the build. You must enable network access in your Copr project.

### Via Copr Web UI (Recommended):

1. Navigate to your project: https://copr.fedorainfracloud.org/coprs/YOUR_USERNAME/trustee-rvps/
2. Click the **"Settings"** tab
3. Scroll to **"Other options"** or **"Build options"** section
4. Find **"Enable internet access during builds"**
5. **Check** the checkbox to enable
6. Click **"Save"** button

### Via copr-cli (Alternative):

```bash
# Enable network access for the project
copr-cli modify YOUR_USERNAME/trustee-rvps --enable-net on

# Verify
copr-cli get YOUR_USERNAME/trustee-rvps | grep -i "enable_net"
```

Expected output:
```
enable_net: True
```

**Note**: If you get authentication errors with copr-cli, use the web UI method instead.

---

## Step 2: Prepare Source Tarball

Create a source tarball from the upstream git repository:

```bash
# Navigate to your trustee repository
cd /path/to/your/trustee

# Check current commit
git log --oneline -1

# Set version (matching upstream Cargo.toml)
VERSION="0.1.0"

# Create source tarball from current state
git archive --format=tar.gz --prefix=trustee-main/ HEAD -o trustee-${VERSION}.tar.gz

# Verify tarball was created
ls -lh trustee-${VERSION}.tar.gz
```

**Expected output**:
```
-rw-r--r--. 1 YOUR_USERNAME YOUR_USERNAME 1.2M Oct 15 11:00 trustee-0.1.0.tar.gz
```

---

## Step 3: Build SRPM Locally

Set up your RPM build environment and create the source RPM:

```bash
# Set up RPM build tree (first time only)
rpmdev-setuptree

# Copy spec file to SPECS directory
cp dependencies/trustee-rvps-no-vendor.spec ~/rpmbuild/SPECS/trustee-rvps.spec

# Copy source tarball to SOURCES directory
cp trustee-0.1.0.tar.gz ~/rpmbuild/SOURCES/

# Build the source RPM
cd ~/rpmbuild/SPECS
rpmbuild -bs trustee-rvps.spec

# Verify SRPM was created
ls -lh ~/rpmbuild/SRPMS/trustee-rvps-*.src.rpm
```

**Expected output**:
```
Wrote: /home/YOUR_USERNAME/rpmbuild/SRPMS/trustee-rvps-0.1.0-1.fc42.src.rpm
-rw-r--r--. 1 YOUR_USERNAME YOUR_USERNAME 1.3M Oct 15 11:05 trustee-rvps-0.1.0-1.fc42.src.rpm
```

---

## Step 4: Submit Build to Copr

### Via Copr Web UI (Easiest):

1. Navigate to your project: https://copr.fedorainfracloud.org/coprs/YOUR_USERNAME/trustee-rvps/
2. Click **"Builds"** tab
3. Click **"New Build"** button
4. Select **"Upload"** tab
5. Click **"Browse"** and select your SRPM file: `~/rpmbuild/SRPMS/trustee-rvps-0.1.0-1.fc42.src.rpm`
6. Click **"Build"**

### Via copr-cli (Alternative):

```bash
# Submit SRPM to Copr
copr-cli build YOUR_USERNAME/trustee-rvps ~/rpmbuild/SRPMS/trustee-rvps-0.1.0-1.fc42.src.rpm

# Note the build ID from the output
```

---

## Step 5: Monitor Build Progress

### Via Web UI:

1. Navigate to: https://copr.fedorainfracloud.org/coprs/YOUR_USERNAME/trustee-rvps/builds/
2. Click on the latest build (should be at the top)
3. Click on **"fedora-42-x86_64"** to view live build log
4. Watch the build progress in real-time

### Via CLI:

```bash
# List recent builds
copr-cli list-builds YOUR_USERNAME/trustee-rvps | head -5

# Watch specific build (use build ID from output)
copr-cli watch-build BUILD_ID

# Example:
# copr-cli watch-build 12345678
```

### Expected Build Stages:

The build will go through these stages:

1. **Installing build dependencies** (~2-3 minutes)
   ```
   Installing: rust cargo gcc protobuf-compiler git systemd-rpm-macros
   ```

2. **Downloading Rust crate dependencies** (~5-10 minutes)
   ```
   Downloading crates ...
   Downloaded anyhow v1.0
   Downloaded tokio v1.x
   Downloaded tonic v0.12
   [... ~30-40 crates ...]
   ```

   This requires network access (enabled in Step 1).

3. **Compiling dependencies** (~10-15 minutes)
   ```
   Compiling proc-macro2 v1.x
   Compiling quote v1.x
   Compiling syn v2.x
   [... many crates ...]
   ```

4. **Building RVPS** (~2-3 minutes)
   ```
   Compiling reference-value-provider-service v0.1.0
   ```

5. **Creating RPM packages** (~1 minute)
   ```
   Wrote: trustee-rvps-0.1.0-1.fc42.x86_64.rpm
   ```

**Total build time**: Approximately 20-30 minutes

**Note**: Build time may vary depending on Copr build queue and server load.

---

## Step 6: Verify Build Success

### Check Build Status:

**Via Web UI:**
- Build status should show: **"succeeded"** (green)
- All selected chroots (e.g., fedora-42-x86_64) should show success

**Via CLI:**
```bash
# Get build info
copr-cli get-build BUILD_ID
```

Expected output:
```
Build: BUILD_ID
State: succeeded
Chroots:
  - fedora-42-x86_64: succeeded
```

### Download and Inspect Built Packages:

```bash
# Download build artifacts to local directory
mkdir -p /tmp/rvps-build
copr-cli download-build BUILD_ID -d /tmp/rvps-build/

# List files in the built RPM
rpm -qpl /tmp/rvps-build/fedora-42-x86_64/trustee-rvps-0.1.0-*.x86_64.rpm
```

**Expected files**:
```
/etc/trustee/rvps.json
/usr/bin/rvps
/usr/bin/rvps-tool
/usr/lib/systemd/system/trustee-rvps.service
/usr/share/doc/trustee-rvps/README.md
/usr/share/licenses/trustee-rvps/LICENSE
/var/lib/trustee
/var/lib/trustee/rvps
```

### Verify Package Metadata:

```bash
# Check package info
rpm -qpi /tmp/rvps-build/fedora-42-x86_64/trustee-rvps-0.1.0-*.x86_64.rpm

# Check dependencies
rpm -qpR /tmp/rvps-build/fedora-42-x86_64/trustee-rvps-0.1.0-*.x86_64.rpm
```

---

## Step 7: Test Installation

### Enable Copr Repository:

On a Fedora 42 test system:

```bash
# Enable your Copr repository
sudo dnf copr enable YOUR_USERNAME/trustee-rvps

# Verify repository is enabled
dnf repolist | grep trustee-rvps
```

### Install the Package:

```bash
# Install trustee-rvps package
sudo dnf install trustee-rvps

# Verify installation
rpm -q trustee-rvps
```

### Verify Binaries:

```bash
# Check rvps binary
rvps --version
# Expected output: rvps 0.1.0 (or similar)

# Check rvps-tool binary
rvps-tool --version
# Expected output: rvps-tool 0.1.0

# View help
rvps --help
rvps-tool --help
```

### Test Systemd Service:

```bash
# Check service status (should be inactive/dead initially)
systemctl status trustee-rvps

# Start the service
sudo systemctl start trustee-rvps

# Check service is running
systemctl status trustee-rvps
# Expected: Active: active (running)

# Enable service to start on boot
sudo systemctl enable trustee-rvps

# Verify service is listening on port 50003
sudo ss -tlnp | grep 50003
# Expected: LISTEN on 0.0.0.0:50003
```

### Check Logs:

```bash
# View service logs
sudo journalctl -u trustee-rvps --no-pager | tail -20

# Follow logs in real-time
sudo journalctl -u trustee-rvps -f
```

### Verify Configuration:

```bash
# Check default configuration file
cat /etc/trustee/rvps.json

# Expected content:
# {
#     "storage": {
#         "type": "LocalFs",
#         "file_path": "/var/lib/trustee/rvps/reference_values"
#     }
# }

# Verify data directory exists
ls -la /var/lib/trustee/rvps/
# Expected: drwxr-x--- trustee trustee
```

---

## Troubleshooting

### Issue 1: Build Fails - "Failed to download dependencies"

**Symptom**:
```
error: failed to fetch `https://crates.io/api/v1/crates/...`
Caused by: network failure
```

**Cause**: Network access not enabled in Copr project settings

**Solution**:
1. Go to https://copr.fedorainfracloud.org/coprs/YOUR_USERNAME/trustee-rvps/
2. Click "Settings" tab
3. Enable "Enable internet access during builds"
4. Save settings
5. Rebuild: Click "Builds" → Select failed build → Click "Repeat Build"

### Issue 2: Build Fails - "could not find `Cargo.toml`"

**Symptom**:
```
error: could not find `Cargo.toml` in `/builddir/build/BUILD/trustee-main` or any parent directory
```

**Cause**: Incorrect working directory in spec file

**Solution**: Verify spec file `%build` section includes:
```spec
%build
cd rvps
cargo build --release --locked
```

### Issue 3: Build Fails - Protobuf Compilation Error

**Symptom**:
```
error: failed to run custom build command for `tonic-build`
protoc: not found
```

**Cause**: Missing `protobuf-compiler` in BuildRequires

**Solution**: Already included in the spec file. Verify spec has:
```spec
BuildRequires:  protobuf-compiler >= 3.15
```

If issue persists, check Fedora 42 has protobuf-compiler available.

### Issue 4: Service Fails to Start - Permission Denied

**Symptom**:
```
systemctl status trustee-rvps
Main PID: ... (code=exited, status=1/FAILURE)
```

**Cause**: SELinux denial or incorrect permissions on `/var/lib/trustee/rvps/`

**Solution**:
```bash
# Check SELinux denials
sudo ausearch -m avc -ts recent | grep rvps

# Fix directory permissions
sudo chown -R trustee:trustee /var/lib/trustee/rvps/
sudo chmod 750 /var/lib/trustee/rvps/

# Restart service
sudo systemctl restart trustee-rvps
```

### Issue 5: Port 50003 Already in Use

**Symptom**:
```
journalctl -u trustee-rvps
Error: Address already in use
```

**Cause**: Another service is using port 50003

**Solution**:
```bash
# Check what's using port 50003
sudo ss -tlnp | grep 50003

# Either stop the conflicting service, or
# Change RVPS port in /etc/trustee/rvps.json (requires upstream support for config)
```

### Issue 6: copr-cli Authentication Errors

**Symptom**:
```
Error: Operation requires API authentication
Error: Can not get session ... Ticket expired
```

**Solution**: Use the Copr web UI instead, or configure API token:

1. Get API token: https://copr.fedorainfracloud.org/api/
2. Click "Generate a new token"
3. Save configuration to `~/.config/copr`:
   ```bash
   mkdir -p ~/.config
   # Paste the configuration shown on the page
   ```

---

## Maintenance and Updates

### Rebuilding for New Upstream Versions:

When upstream releases a new version or you want to build from a newer commit:

```bash
# 1. Update your local repository
cd /path/to/your/trustee
git pull upstream main

# 2. Check the new commit
git log --oneline -1

# 3. Update version in spec file
# Edit dependencies/trustee-rvps-no-vendor.spec
# Update: Version: 0.16.0 (or appropriate version)
# Update: %changelog with changes

# 4. Create new source tarball
VERSION="0.16.0"
git archive --format=tar.gz --prefix=trustee-main/ HEAD -o trustee-${VERSION}.tar.gz

# 5. Build new SRPM
cp dependencies/trustee-rvps-no-vendor.spec ~/rpmbuild/SPECS/trustee-rvps.spec
cp trustee-${VERSION}.tar.gz ~/rpmbuild/SOURCES/
cd ~/rpmbuild/SPECS
rpmbuild -bs trustee-rvps.spec

# 6. Submit new build to Copr
# Via web UI or:
copr-cli build YOUR_USERNAME/trustee-rvps ~/rpmbuild/SRPMS/trustee-rvps-${VERSION}-1.fc42.src.rpm
```

### Monitoring Copr Repository:

```bash
# Check repository status
copr-cli list

# View package details
copr-cli get-package YOUR_USERNAME/trustee-rvps --name trustee-rvps

# Check build history
copr-cli list-builds YOUR_USERNAME/trustee-rvps
```

---

## Additional Configuration

### Customizing RVPS Configuration:

After installation, you can modify the configuration file:

```bash
# Edit configuration
sudo vi /etc/trustee/rvps.json

# Example: Change storage type to LocalJson
{
    "storage": {
        "type": "LocalJson",
        "file_path": "/var/lib/trustee/rvps/reference_values.json"
    }
}

# Restart service to apply changes
sudo systemctl restart trustee-rvps
```

### Changing Listen Address/Port:

The default listen address is `0.0.0.0:50003`. To change it:

```bash
# Edit systemd service
sudo systemctl edit trustee-rvps

# Add override:
[Service]
ExecStart=
ExecStart=/usr/bin/rvps --config /etc/trustee/rvps.json --address 127.0.0.1:50003

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart trustee-rvps
```

### Firewall Configuration:

If RVPS needs to be accessible from other hosts:

```bash
# Open port 50003 in firewall
sudo firewall-cmd --add-port=50003/tcp --permanent
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-ports
```

---

## Integration with Attestation Service

RVPS is designed to work with the Attestation Service. Example AS configuration:

```json
{
    "work_dir": "/var/lib/trustee/attestation-service/",
    "rvps_config": {
        "type": "GrpcRemote",
        "address": "127.0.0.1:50003"
    }
}
```

**Note**: If AS and RVPS run on different hosts, ensure:
- Port 50003 is accessible over the network
- Firewall rules allow the connection
- Consider using TLS when supported by upstream

---

## Files and Locations

### Spec File:
- Location: `/path/to/your/trustee/dependencies/trustee-rvps-no-vendor.spec`
- Purpose: RPM spec file for building RVPS package

### Build Guide (This File):
- Location: `/path/to/your/trustee/dependencies/copr/BUILD-GUIDE.md`
- Purpose: Complete guide for building RVPS in Copr

### Related Documentation:
- RVPS Analysis: `../dependencies-rvps.md`
- General Dependencies: `../dependencies-analysis.md`
- RHEL Verification: `../rhel-10.2-verification.md`

---

## Quick Reference

### Complete Build Commands (Quick Copy):

```bash
# 1. Create source tarball
cd /path/to/your/trustee
VERSION="0.1.0"
git archive --format=tar.gz --prefix=trustee-main/ HEAD -o trustee-${VERSION}.tar.gz

# 2. Build SRPM
cp dependencies/trustee-rvps-no-vendor.spec ~/rpmbuild/SPECS/trustee-rvps.spec
cp trustee-${VERSION}.tar.gz ~/rpmbuild/SOURCES/
cd ~/rpmbuild/SPECS
rpmbuild -bs trustee-rvps.spec

# 3. Enable network access (web UI or CLI)
copr-cli modify YOUR_USERNAME/trustee-rvps --enable-net on

# 4. Submit build (web UI or CLI)
copr-cli build YOUR_USERNAME/trustee-rvps ~/rpmbuild/SRPMS/trustee-rvps-${VERSION}-1.fc42.src.rpm

# 5. Install and test
sudo dnf copr enable YOUR_USERNAME/trustee-rvps
sudo dnf install trustee-rvps
sudo systemctl start trustee-rvps
systemctl status trustee-rvps
```

---

## Support and Resources

### Documentation:
- **Upstream RVPS**: https://github.com/confidential-containers/trustee/tree/main/rvps
- **Copr Documentation**: https://docs.pagure.org/copr.copr/
- **Fedora Rust Packaging**: https://docs.fedoraproject.org/en-US/packaging-guidelines/Rust/

### Community:
- **Trustee GitHub**: https://github.com/confidential-containers/trustee
- **Confidential Containers**: https://confidentialcontainers.org/

### Your Resources:
- **Copr Project**: https://copr.fedorainfracloud.org/coprs/YOUR_USERNAME/trustee-rvps/
- **Source Repository**: https://github.com/YOUR_USERNAME/trustee (if applicable)

---

**Last Updated**: 2025-10-15
**Maintainer**: Your Name <your.email@example.com>
**Version**: 0.1.0
