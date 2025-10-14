# RVPS Fedora 42 Packaging Step-by-Step Guide

**Target:** Create and test RVPS component package for Fedora 42 in Copr<br>
**Component:** Reference Value Provider Service (RVPS)<br>
**Version:** Based on commit 42f5c66<br>
**Last Updated:** 2025-10-15

---

## Table of Contents

1. [Preparation](#phase-1-preparation)
2. [Create RPM Spec File](#phase-2-create-rpm-spec-file)
3. [Local Testing](#phase-3-local-testing)
4. [Copr Setup](#phase-4-copr-setup)
5. [Copr Build](#phase-5-copr-build)
6. [Testing Built Package](#phase-6-testing-built-package)
7. [Documentation and Refinement](#phase-7-documentation-and-refinement)
8. [Key Files Summary](#key-files-youll-need-to-create)
9. [Important Considerations](#important-considerations)

---

## Phase 1: Preparation

### Step 1: Set up your Copr account

**Create and configure Copr access:**

```bash
# Create account at https://copr.fedorainfracloud.org/
# Generate API token from your account settings

# Install copr-cli
sudo dnf install copr-cli

# Configure credentials
# Edit ~/.config/copr with your API token
```

**Copr configuration file format (`~/.config/copr`):**
```ini
[copr-cli]
login = your_username
username = your_username
token = your_api_token
copr_url = https://copr.fedorainfracloud.org
```

### Step 2: Prepare the upstream source

**Clone and prepare source:**

```bash
# Clone the trustee repository
git clone https://github.com/confidential-containers/trustee.git
cd trustee

# Identify the exact commit/tag you want to package
git log --oneline -1
# Currently: commit 42f5c66

# Create a source tarball from that commit
VERSION=0.1.0
git archive --format=tar.gz --prefix=trustee-${VERSION}/ \
  42f5c66 -o trustee-${VERSION}.tar.gz

# Extract to prepare vendor tarball
tar xzf trustee-${VERSION}.tar.gz
cd trustee-${VERSION}

# Generate vendor tarball (REQUIRED for Fedora builds)
cargo vendor
tar czf ../vendor-${VERSION}.tar.gz vendor/

cd ..
```

**Important:** The vendor tarball is mandatory because Copr builds don't have network access.

---

## Phase 2: Create RPM Spec File

### Step 3: Write the spec file (`trustee-rvps.spec`)

**Create comprehensive RPM spec file with all required sections:**

```spec
Name:           trustee-rvps
Version:        0.1.0
Release:        1%{?dist}
Summary:        Reference Value Provider Service for Trustee

License:        Apache-2.0
URL:            https://github.com/confidential-containers/trustee
Source0:        https://github.com/confidential-containers/trustee/archive/%{version}/trustee-%{version}.tar.gz
Source1:        vendor-%{version}.tar.gz
Source2:        trustee-rvps.service

BuildRequires:  rust >= 1.70
BuildRequires:  cargo >= 1.70
BuildRequires:  gcc
BuildRequires:  protobuf-compiler >= 3.15
BuildRequires:  git
BuildRequires:  systemd-rpm-macros

Requires:       glibc
Requires(pre):  shadow-utils
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

%description
RVPS (Reference Value Provider Service) receives software supply chain
provenances, verifies them, and provides reference values to the
Attestation Service for confidential computing attestation workflows.

RVPS runs as a standalone gRPC service (port 50003) that processes
different provenance types and stores reference values in persistent
storage (LocalFs or LocalJson).

%prep
%autosetup -n trustee-%{version} -p1

# Extract vendor tarball
tar xzf %{SOURCE1}

# Configure cargo to use vendored dependencies
mkdir -p .cargo
cat >.cargo/config.toml <<EOF
[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "vendor"
EOF

%build
cd rvps
cargo build --release --locked --offline

%install
# Install binaries
install -D -m 0755 target/release/rvps %{buildroot}%{_bindir}/rvps
install -D -m 0755 target/release/rvps-tool %{buildroot}%{_bindir}/rvps-tool

# Install systemd unit
install -D -m 0644 %{SOURCE2} %{buildroot}%{_unitdir}/trustee-rvps.service

# Install default config
install -d -m 0755 %{buildroot}%{_sysconfdir}/trustee
cat >%{buildroot}%{_sysconfdir}/trustee/rvps.json <<EOF
{
    "storage": {
        "type": "LocalFs",
        "file_path": "/var/lib/trustee/rvps/reference_values"
    }
}
EOF

# Create data directory
install -d -m 0750 %{buildroot}%{_sharedstatedir}/trustee/rvps

%pre
getent group trustee >/dev/null || groupadd -r trustee
getent passwd trustee >/dev/null || \
    useradd -r -g trustee -d %{_sharedstatedir}/trustee -s /sbin/nologin \
    -c "Trustee service account" trustee
exit 0

%post
%systemd_post trustee-rvps.service

%preun
%systemd_preun trustee-rvps.service

%postun
%systemd_postun_with_restart trustee-rvps.service

%files
%license LICENSE
%doc rvps/README.md
%{_bindir}/rvps
%{_bindir}/rvps-tool
%{_unitdir}/trustee-rvps.service
%config(noreplace) %{_sysconfdir}/trustee/rvps.json
%dir %attr(0755,root,root) %{_sysconfdir}/trustee
%dir %attr(0750,root,root) %{_sharedstatedir}/trustee
%dir %attr(0750,trustee,trustee) %{_sharedstatedir}/trustee/rvps

%changelog
* Wed Oct 15 2025 Your Name <your.email@example.com> - 0.1.0-1
- Initial package for Fedora 42
- Based on commit 42f5c66 from upstream
- Standalone RVPS service with gRPC API (port 50003)
```

### Step 4: Create the systemd service file

**Create `trustee-rvps.service`:**

```ini
[Unit]
Description=Trustee Reference Value Provider Service (RVPS)
Documentation=https://github.com/confidential-containers/trustee/tree/main/rvps
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=trustee
Group=trustee
ExecStart=/usr/bin/rvps --config /etc/trustee/rvps.json --address 0.0.0.0:50003
Restart=on-failure
RestartSec=5s

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/trustee/rvps
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictNamespaces=true
LockPersonality=true
MemoryDenyWriteExecute=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=rvps

[Install]
WantedBy=multi-user.target
```

### Step 5: Create initial configuration

**Example `rvps.json` config file** (embedded in spec file %install section):

```json
{
    "storage": {
        "type": "LocalFs",
        "file_path": "/var/lib/trustee/rvps/reference_values"
    }
}
```

**Note:** This is already included in the spec file's %install section above.

---

## Phase 3: Local Testing

### Step 6: Test build locally with mock

**Create SRPM:**

```bash
# Set up rpmbuild directories
rpmdev-setuptree

# Copy spec file and sources
cp trustee-rvps.spec ~/rpmbuild/SPECS/
cp trustee-0.1.0.tar.gz ~/rpmbuild/SOURCES/
cp vendor-0.1.0.tar.gz ~/rpmbuild/SOURCES/
cp trustee-rvps.service ~/rpmbuild/SOURCES/

# Build SRPM
cd ~/rpmbuild/SPECS
rpmbuild -bs trustee-rvps.spec

# The SRPM will be in ~/rpmbuild/SRPMS/
```

**Test build in mock for Fedora 42:**

```bash
# Test build in mock environment
mock -r fedora-42-x86_64 rebuild ~/rpmbuild/SRPMS/trustee-rvps-0.1.0-1.fc42.src.rpm

# Results will be in:
# /var/lib/mock/fedora-42-x86_64/result/
```

**Watch the build:**

```bash
# Follow the build log
tail -f /var/lib/mock/fedora-42-x86_64/result/build.log
```

### Step 7: Verify the built RPM

**Inspect RPM contents:**

```bash
# List files in the RPM
rpm -qpl /var/lib/mock/fedora-42-x86_64/result/trustee-rvps-0.1.0-1.fc42.x86_64.rpm

# Expected output:
# /etc/trustee/rvps.json
# /usr/bin/rvps
# /usr/bin/rvps-tool
# /usr/lib/systemd/system/trustee-rvps.service
# /usr/share/doc/trustee-rvps/README.md
# /usr/share/licenses/trustee-rvps/LICENSE
# /var/lib/trustee
# /var/lib/trustee/rvps
```

**Check file ownership and permissions:**

```bash
# List files with verbose info
rpm -qplv /var/lib/mock/fedora-42-x86_64/result/trustee-rvps-0.1.0-1.fc42.x86_64.rpm

# Verify:
# - Binaries are 0755 owned by root
# - Config file is 0644 owned by root
# - /var/lib/trustee/rvps is 0750 owned by trustee:trustee
```

**Verify dependencies:**

```bash
# Check runtime dependencies
rpm -qp --requires /var/lib/mock/fedora-42-x86_64/result/trustee-rvps-0.1.0-1.fc42.x86_64.rpm

# Should include: glibc, systemd, etc.

# Check what the package provides
rpm -qp --provides /var/lib/mock/fedora-42-x86_64/result/trustee-rvps-0.1.0-1.fc42.x86_64.rpm
```

### Step 8: Test installation in clean environment

**Option A: Install in mock environment:**

```bash
# Install the built RPM in mock
mock -r fedora-42-x86_64 --install \
  /var/lib/mock/fedora-42-x86_64/result/trustee-rvps-0.1.0-1.fc42.x86_64.rpm

# Shell into the mock environment to test
mock -r fedora-42-x86_64 --shell

# Inside mock shell:
rvps --version
rvps-tool --version
systemctl status trustee-rvps
```

**Option B: Test in a container:**

```bash
# Start a Fedora 42 container
podman run -it --rm -v /var/lib/mock/fedora-42-x86_64/result:/rpms:Z fedora:42 bash

# Inside container:
dnf install -y /rpms/trustee-rvps-0.1.0-1.fc42.x86_64.rpm

# Test basic functionality
rvps --version
rvps-tool --help
```

### Step 9: Verify package functionality

**Run comprehensive checks:**

```bash
# Check binaries exist and run
rvps --version
# Expected: rvps 0.1.0 (or similar)

rvps-tool --version
# Expected: rvps-tool 0.1.0

# Verify systemd unit is installed
systemctl status trustee-rvps
# Expected: Loaded: loaded (/usr/lib/systemd/system/trustee-rvps.service)

# Check user/group creation
getent passwd trustee
# Expected: trustee:x:...:Trustee service account:/var/lib/trustee:/sbin/nologin

getent group trustee
# Expected: trustee:x:...

# Verify file permissions
ls -la /var/lib/trustee/rvps/
# Expected: drwxr-x--- trustee trustee

ls -la /etc/trustee/
# Expected: -rw-r--r-- root root rvps.json

# Try starting the service
systemctl start trustee-rvps
systemctl status trustee-rvps

# Check if port is listening
ss -tlnp | grep 50003
# Expected: LISTEN on 0.0.0.0:50003

# Check logs
journalctl -u trustee-rvps --no-pager | tail -20
```

---

## Phase 4: Copr Setup

### Step 10: Create Copr project

**Option A: Using copr-cli:**

```bash
# Create new Copr project
copr-cli create trustee-rvps \
  --chroot fedora-42-x86_64 \
  --description "RVPS (Reference Value Provider Service) for Trustee - Confidential Computing attestation" \
  --instructions "https://github.com/confidential-containers/trustee" \
  --disable_appstream true

# Add additional architectures if needed
copr-cli modify-chroot trustee-rvps/fedora-42-aarch64 --enable
```

**Option B: Using web UI:**

1. Navigate to https://copr.fedorainfracloud.org/
2. Click "New Project"
3. Fill in:
   - **Project name:** trustee-rvps
   - **Description:** RVPS (Reference Value Provider Service) for Trustee
   - **Instructions:** Link to upstream documentation
   - **Chroots:** Select fedora-42-x86_64 (and other architectures if needed)
   - **Build options:** Enable internet access OFF (not needed with vendored deps)

### Step 11: Prepare source for Copr

**Three main options for source delivery:**

**Option A: Upload SRPM (Simplest)**
- Upload the pre-built SRPM directly
- No additional configuration needed
- Good for testing and initial builds

**Option B: SCM (Git repository)**
- Point Copr to a git repository containing spec file and sources
- Automatic rebuilds when git repo changes
- Best for ongoing maintenance

**Option C: URL (Direct URLs)**
- Provide direct URLs to spec file and source tarballs
- Sources must be publicly accessible
- Good for official releases

### Step 12: Upload sources to hosting

**You need to host the source tarballs somewhere accessible:**

**Option 1: GitHub Releases**
```bash
# Create a GitHub release for your RPM sources
# Upload trustee-0.1.0.tar.gz to release
# Upload vendor-0.1.0.tar.gz to release (warning: can be 50-100MB+)

# Update spec file Source0 and Source1 URLs:
# Source0: https://github.com/yourusername/trustee-rpm/releases/download/v0.1.0/trustee-0.1.0.tar.gz
# Source1: https://github.com/yourusername/trustee-rpm/releases/download/v0.1.0/vendor-0.1.0.tar.gz
```

**Option 2: Fedora lookaside cache (for official Fedora packages)**
```bash
# Upload to Fedora dist-git lookaside cache
# Requires being a Fedora packager
fedpkg upload trustee-0.1.0.tar.gz
fedpkg upload vendor-0.1.0.tar.gz
```

**Option 3: Include in SCM repository**
```bash
# For smaller sources, include directly in git repo
# Not recommended for vendor tarball (too large)
git lfs track "*.tar.gz"
git add trustee-0.1.0.tar.gz vendor-0.1.0.tar.gz
git commit -m "Add source tarballs"
```

**Ensure trustee-rvps.service is accessible:**
- Include in git repository with spec file, OR
- Embed directly in spec file (as shown in Step 3), OR
- Host separately and reference in Source2

---

## Phase 5: Copr Build

### Step 13: Submit build to Copr

**Method 1: Build from SRPM**

```bash
# Upload and build SRPM
copr-cli build trustee-rvps ~/rpmbuild/SRPMS/trustee-rvps-0.1.0-1.fc42.src.rpm

# Watch build progress
copr-cli watch-build <build-id>
```

**Method 2: Build from SCM (git repository)**

```bash
# First, create a git repository with:
# - trustee-rvps.spec
# - trustee-rvps.service
# - .gitignore
# - README.md (optional)

# Then submit SCM build
copr-cli buildscm trustee-rvps \
  --clone-url https://github.com/yourusername/trustee-rpm \
  --commit main \
  --subdir . \
  --spec trustee-rvps.spec \
  --type git \
  --method make_srpm

# For automatic rebuilds on commit:
copr-cli edit-package-scm trustee-rvps \
  --webhook-rebuild on
```

**Method 3: Build from PyPI/URL (less common)**

```bash
# Build from direct URLs
copr-cli build trustee-rvps \
  --url https://example.com/trustee-rvps-0.1.0-1.fc42.src.rpm
```

### Step 14: Monitor build

**Watch build in web UI:**
1. Navigate to https://copr.fedorainfracloud.org/coprs/yourusername/trustee-rvps/
2. Click on "Builds" tab
3. Click on the build number
4. Watch live build logs

**Watch build via CLI:**

```bash
# List builds
copr-cli list-builds trustee-rvps

# Watch specific build
copr-cli watch-build <build-id>

# Download build logs if build fails
copr-cli download-build <build-id>
```

**Common issues to watch for:**

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Missing BuildRequires** | "command not found" during build | Add missing package to BuildRequires |
| **Cargo vendoring not working** | "Updating crates.io index" (network access) | Verify .cargo/config.toml is created correctly |
| **Protobuf compilation failures** | "protoc: not found" or protobuf errors | Ensure protobuf-compiler >= 3.15 in BuildRequires |
| **Missing files in %files** | "Installed (but unpackaged) file(s) found" | Add missing files to %files section |
| **Rust version too old** | Compilation errors with modern Rust syntax | Verify rust >= 1.70 requirement |
| **Wrong permissions** | rpmlint errors about permissions | Fix %attr() directives in %files |

---

## Phase 6: Testing Built Package

### Step 15: Install from Copr

**Enable Copr repository:**

```bash
# Enable your Copr repository
sudo dnf copr enable yourusername/trustee-rvps

# Repository will be added to /etc/yum.repos.d/
# File: _copr:copr.fedorainfracloud.org:yourusername:trustee-rvps.repo
```

**Install the package:**

```bash
# Install from Copr
sudo dnf install trustee-rvps

# Or install with dependencies
sudo dnf install -y trustee-rvps

# Verify installation
rpm -qi trustee-rvps
```

### Step 16: Run the Testing Checklist

**Complete testing checklist from dependencies-rvps.md section 12:**

**Build Tests:**
- [ ] Build succeeds in Copr environment
- [ ] No build warnings or errors
- [ ] Binary packages created for all enabled architectures

**Binary Tests:**
```bash
# Test binaries execute
rvps --version
rvps-tool --version
rvps --help
rvps-tool --help
```
- [ ] `rvps --version` works and shows correct version
- [ ] `rvps-tool --version` works and shows correct version

**Service Tests:**
```bash
# Test systemd service
sudo systemctl start trustee-rvps
sudo systemctl status trustee-rvps
sudo systemctl enable trustee-rvps
```
- [ ] `systemctl start trustee-rvps` succeeds
- [ ] Service status shows "active (running)"

**Network Tests:**
```bash
# Check port is listening
sudo ss -tlnp | grep 50003
sudo netstat -tlnp | grep 50003
```
- [ ] Port 50003 is open and listening
- [ ] Process is rvps (not another service)

**Functionality Tests:**
```bash
# Test basic functionality with rvps-tool
# (Requires creating sample provenance data)

# Example: Register sample provenance
rvps-tool register --help

# Example: Query reference values
rvps-tool query --help
```
- [ ] Can register sample provenance with `rvps-tool register`
- [ ] Can query reference values with `rvps-tool query`
- [ ] Verify values stored in `/var/lib/trustee/rvps/`

**Permission Tests:**
```bash
# Verify file permissions
ls -la /var/lib/trustee/rvps/
ls -la /etc/trustee/
stat /var/lib/trustee/rvps/

# Verify ownership
ls -ln /var/lib/trustee/rvps/
```
- [ ] `/var/lib/trustee/rvps/` owned by `trustee:trustee`, mode `0750`
- [ ] Binaries in `/usr/bin/` executable by all (mode `0755`)
- [ ] Config in `/etc/trustee/` readable by all (mode `0644`)

**SELinux Tests:**
```bash
# Check SELinux status
getenforce

# Check for denials
sudo ausearch -m avc -ts recent | grep rvps
sudo sealert -a /var/log/audit/audit.log
```
- [ ] No SELinux denials in audit log
- [ ] Service runs correctly in SELinux enforcing mode

**Service Management Tests:**
```bash
# Test service restart
sudo systemctl restart trustee-rvps
sudo systemctl status trustee-rvps

# Test service stop/start
sudo systemctl stop trustee-rvps
sudo systemctl start trustee-rvps

# Check data persists
ls -la /var/lib/trustee/rvps/
```
- [ ] `systemctl restart trustee-rvps` works without data loss
- [ ] Service can be stopped and started cleanly

**Logging Tests:**
```bash
# Check logs
sudo journalctl -u trustee-rvps
sudo journalctl -u trustee-rvps -f
sudo journalctl -u trustee-rvps --since "1 hour ago"
```
- [ ] Logs appear in `journalctl -u trustee-rvps`
- [ ] Log level is appropriate
- [ ] No unexpected errors in logs

**Upgrade Tests:**
```bash
# Simulate upgrade (build new version, install over existing)
sudo dnf upgrade trustee-rvps

# Verify
rpm -q trustee-rvps
sudo systemctl status trustee-rvps
ls -la /var/lib/trustee/rvps/
```
- [ ] Package upgrade preserves configuration (`/etc/trustee/rvps.json`)
- [ ] Package upgrade preserves data (`/var/lib/trustee/rvps/`)
- [ ] Service continues running after upgrade

**Uninstall Tests:**
```bash
# Test package removal
sudo systemctl stop trustee-rvps
sudo dnf remove trustee-rvps

# Verify cleanup
rpm -q trustee-rvps
ls -la /usr/bin/rvps
ls -la /var/lib/trustee/rvps/
```
- [ ] Package removal cleans up binaries
- [ ] Package removal cleans up systemd unit
- [ ] Data directory preserved (or removed, depending on policy)

### Step 17: Test on RHEL 10.2 (optional but recommended)

**Create Copr chroot for RHEL 10 (if available):**

```bash
# Check available chroots
copr-cli list-chroots | grep rhel

# Add RHEL 10 chroot to your project
copr-cli edit-chroot trustee-rvps/rhel-10-x86_64 --enable
```

**Or test manually on RHEL 10.2 Beta system:**

```bash
# Build for CentOS Stream 10 in Copr (closest to RHEL 10)
copr-cli edit-chroot trustee-rvps/centos-stream-10-x86_64 --enable
copr-cli build trustee-rvps --chroot centos-stream-10-x86_64

# Transfer RPM to RHEL 10.2 Beta system at 10.0.184.129
scp /path/to/trustee-rvps-*.rpm root@10.0.184.129:/tmp/

# Install on RHEL system
ssh root@10.0.184.129 'dnf install -y /tmp/trustee-rvps-*.rpm'

# Test on RHEL
ssh root@10.0.184.129 'systemctl start trustee-rvps'
ssh root@10.0.184.129 'systemctl status trustee-rvps'
ssh root@10.0.184.129 'ss -tlnp | grep 50003'
ssh root@10.0.184.129 'rvps --version'
```

**Verify RHEL compatibility:**
- [ ] Package installs on RHEL 10.2 without errors
- [ ] All dependencies available in RHEL 10.2 repositories
- [ ] Service starts and runs correctly on RHEL
- [ ] No SELinux denials on RHEL (enforcing mode)

---

## Phase 7: Documentation and Refinement

### Step 18: Document the build process

**Create comprehensive documentation:**

**README.md for your RPM repository:**

```markdown
# Trustee RVPS RPM Package

RPM packaging for RVPS (Reference Value Provider Service) from the
[Confidential Containers Trustee](https://github.com/confidential-containers/trustee) project.

## Installation

### From Copr

```bash
sudo dnf copr enable yourusername/trustee-rvps
sudo dnf install trustee-rvps
```

### Building from Source

See [BUILDING.md](BUILDING.md) for detailed build instructions.

## Usage

Start the service:
```bash
sudo systemctl start trustee-rvps
sudo systemctl enable trustee-rvps
```

Check status:
```bash
sudo systemctl status trustee-rvps
journalctl -u trustee-rvps -f
```

Configuration file: `/etc/trustee/rvps.json`

## Documentation

- [Upstream RVPS Documentation](https://github.com/confidential-containers/trustee/tree/main/rvps)
- [Packaging Analysis](dependencies-rvps.md)

## License

Apache-2.0 (same as upstream)
```

**Document Fedora-specific patches (if any):**
- Create `patches/` directory for any Fedora-specific patches
- Document why each patch is needed
- Reference patches in spec file with `Patch0:`, `Patch1:`, etc.

**Note deviations from upstream:**
- Document any differences in configuration defaults
- Note any features disabled for packaging
- Explain any Fedora-specific build flags

**Include example usage:**
- Provide sample provenance files for testing
- Include example `rvps-tool` commands
- Document integration with Attestation Service

### Step 19: Set up automatic rebuilds (optional)

**Configure Copr to watch upstream git repository:**

```bash
# Enable webhook for automatic builds
copr-cli edit-package-scm trustee-rvps \
  --webhook-rebuild on \
  --clone-url https://github.com/yourusername/trustee-rpm \
  --commit main \
  --spec trustee-rvps.spec

# Get webhook URL
copr-cli get-package trustee-rvps --name trustee-rvps
```

**Set up GitHub webhook:**
1. Go to your GitHub repository settings
2. Navigate to Webhooks → Add webhook
3. Paste Copr webhook URL
4. Select "Just the push event"
5. Ensure "Active" is checked

**Configure build triggers:**
- Trigger builds on git tags (for releases)
- Trigger builds on commits to main branch
- Optional: Trigger on pull requests for testing

### Step 20: Request feedback

**Share with community:**

```bash
# Make Copr repository public (if not already)
copr-cli modify trustee-rvps --unlisted-on-hp off

# Share repository URL
# https://copr.fedorainfracloud.org/coprs/yourusername/trustee-rvps/
```

**Request testing:**
1. Post to Trustee community channels
2. Share on Fedora packaging mailing lists (if going official)
3. Request testing on different Fedora/RHEL versions
4. Ask for architecture testing (x86_64, aarch64, etc.)

**Address feedback:**
- Fix reported issues promptly
- Update spec file based on feedback
- Run rpmlint and fix warnings
- Consider submitting to official Fedora if mature

---

## Key Files You'll Need to Create

### 1. trustee-rvps.spec
Main RPM spec file with all package metadata, build instructions, and scriptlets.

**Location:** Root of your RPM git repository

**See:** [Step 3](#step-3-write-the-spec-file-trustee-rvpsspec) for complete spec file

### 2. trustee-rvps.service
Systemd unit file for RVPS service.

**Location:** Same directory as spec file, or in `sources/` subdirectory

**See:** [Step 4](#step-4-create-the-systemd-service-file) for complete service file

### 3. rvps.json
Example configuration file (can be embedded in spec or separate).

**Location:** Can be embedded in spec %install section, or separate file in `sources/`

**See:** [Step 5](#step-5-create-initial-configuration) for example config

### 4. sources file
List of source URLs (if using Fedora dist-git approach).

**Location:** Root of git repository

**Content:**
```
SHA512 (trustee-0.1.0.tar.gz) = <sha512sum>
SHA512 (vendor-0.1.0.tar.gz) = <sha512sum>
```

### 5. .copr/Makefile
Optional: for Copr SCM builds to customize how SRPM is created.

**Location:** `.copr/Makefile` in git repository

**Example:**
```makefile
SRCDIR := $(shell pwd)
SPEC := trustee-rvps.spec

srpm:
	rpmbuild -bs --define "_sourcedir $(SRCDIR)" \
	             --define "_specdir $(SRCDIR)" \
	             --define "_builddir $(SRCDIR)" \
	             --define "_srcrpmdir $(outdir)" \
	             --define "_rpmdir $(outdir)" \
	             $(SPEC)
```

### 6. .gitignore
Ignore build artifacts in git repository.

**Location:** Root of git repository

**Content:**
```
*.rpm
*.tar.gz
vendor/
.cargo/
target/
*~
*.swp
```

### 7. README.md
Documentation for your RPM package repository.

**Location:** Root of git repository

**See:** [Step 18](#step-18-document-the-build-process) for example content

### 8. BUILDING.md
Detailed build instructions for packagers.

**Location:** Root of git repository

**Should include:**
- Prerequisites
- How to create source tarballs
- How to build locally with mock
- How to submit to Copr
- Troubleshooting common issues

---

## Important Considerations

### Cargo Vendoring

**Why vendoring is mandatory:**
- Network access not available during Copr builds (security policy)
- Ensures reproducible builds (same dependencies every time)
- Fedora policy requires all sources to be available offline

**How to vendor:**
```bash
cd trustee-0.1.0
cargo vendor
tar czf ../vendor-0.1.0.tar.gz vendor/
```

**Vendor tarball characteristics:**
- Large size: typically 50-100MB for RVPS (lighter than KBS)
- Contains all Rust crate dependencies (~30-40 crates for RVPS)
- Must be uploaded to reliable hosting (GitHub releases, lookaside cache)

**Configure cargo in spec file:**
```spec
%prep
tar xzf %{SOURCE1}  # Extract vendor tarball

mkdir -p .cargo
cat >.cargo/config.toml <<EOF
[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "vendor"
EOF
```

### Source URLs

**Requirements for source hosting:**
- URLs must be publicly accessible (no authentication)
- Sources must be stable (not change after upload)
- HTTPS preferred for security

**Good options:**
- **GitHub Releases:** Free, reliable, good for open source
  - Example: `https://github.com/user/repo/releases/download/v0.1.0/file.tar.gz`
- **Fedora lookaside cache:** Official for Fedora packages
  - Requires being a Fedora packager
- **Your own server:** Must be reliable and fast

**Copr source size limits:**
- SRPM upload: ~1GB max
- Individual source files: Check current Copr limits
- Vendor tarball usually fits within limits

### Rust/Cargo in Fedora

**Fedora Rust packaging guidelines:**
- Follow https://docs.fedoraproject.org/en-US/packaging-guidelines/Rust/
- Use `%cargo_*` macros when available (Fedora 37+)
- Always use `--release` for production builds
- Always use `--locked` to use exact dependency versions
- Always use `--offline` to ensure no network access

**Recommended cargo build flags:**
```bash
cargo build --release --locked --offline
```

**Macro alternatives (if available):**
```spec
%cargo_build
# Expands to: cargo build --release -j%{_smp_build_ncpus} --locked
```

**Common Rust build issues:**
- **RUSTFLAGS:** May need to set for Fedora-specific optimizations
- **Debug symbols:** Fedora automatically strips binaries, generates debuginfo
- **Build parallelism:** Use `%{_smp_build_ncpus}` for parallel builds

### Security Considerations

**SELinux testing:**
```bash
# Always test in enforcing mode
getenforce  # Should be "Enforcing"

# Check for denials
sudo ausearch -m avc -ts recent | grep rvps
sudo sealert -a /var/log/audit/audit.log

# If denials found, may need custom policy
# Or adjust file contexts
```

**Systemd security hardening:**
- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Private /tmp directory
- `ProtectSystem=strict` - Read-only /usr, /boot, /etc
- `ProtectHome=true` - Inaccessible /home
- `ReadWritePaths=` - Explicit write permissions only where needed
- Additional hardening in trustee-rvps.service (see Step 4)

**File permissions:**
- Binaries: 0755 (executable by all, writable only by root)
- Config files: 0644 (readable by all, writable only by root)
- Data directories: 0750 (rwx for owner, rx for group, nothing for others)
- Data directory owner: trustee:trustee (dedicated service account)

**Best practices:**
- Never run as root (use dedicated `trustee` user)
- Minimal file system access (ProtectSystem, ProtectHome)
- Restrict network access to needed address families only
- Log to journal for centralized logging
- Use systemd watchdog for health monitoring (future enhancement)

---

## Troubleshooting Common Issues

### Build Failures

**Issue:** "error: no matching package found for `protobuf-compiler`"
```
Solution: Ensure BuildRequires: protobuf-compiler >= 3.15
Check: copr-cli list-chroots to verify Fedora 42 support
```

**Issue:** "Updating crates.io index" during build (network access)
```
Solution: Cargo vendoring not working
Check: .cargo/config.toml is created correctly in %prep
Verify: vendor/ directory extracted from Source1
```

**Issue:** "error: could not find `Cargo.toml`"
```
Solution: Working directory incorrect
Fix: Add "cd rvps" before cargo build in %build section
```

**Issue:** Build runs out of memory
```
Solution: Reduce parallel jobs
Add to %build: export CARGO_BUILD_JOBS=2
Or use: cargo build --jobs 2 ...
```

### Runtime Failures

**Issue:** Service fails to start with "Permission denied"
```
Solution: Check SELinux denials
Commands:
  sudo ausearch -m avc -ts recent
  sudo sealert -a /var/log/audit/audit.log
Fix: Adjust file contexts or create SELinux policy module
```

**Issue:** "Address already in use" for port 50003
```
Solution: Another service using the port
Check: sudo ss -tlnp | grep 50003
Fix: Stop conflicting service or change RVPS port in config
```

**Issue:** Cannot write to /var/lib/trustee/rvps/
```
Solution: Directory permissions incorrect
Check: ls -la /var/lib/trustee/rvps/
Fix: sudo chown -R trustee:trustee /var/lib/trustee/rvps/
      sudo chmod 750 /var/lib/trustee/rvps/
```

### Copr-Specific Issues

**Issue:** Copr build stuck in "pending" state
```
Solution: Too many builds in queue or chroot not available
Check: Copr web UI for build queue status
Wait: Builds usually process within minutes to hours
```

**Issue:** "Source not found" error in Copr
```
Solution: Source URL not accessible
Check: wget <source-url> from command line
Fix: Ensure sources uploaded and URLs correct in spec
```

**Issue:** SRPM upload rejected (too large)
```
Solution: SRPM exceeds Copr size limits
Check: ls -lh *.src.rpm (should be < 1GB)
Fix: Use SCM build instead of SRPM upload
      Or reduce vendor tarball size
```

---

## Next Steps After Successful Build

1. **Monitor Copr repository usage**
   - Check download statistics
   - Review user feedback/issues

2. **Keep package updated**
   - Watch for upstream releases
   - Rebuild for new Fedora versions
   - Update dependencies as needed

3. **Consider official Fedora submission**
   - Join Fedora Packagers group
   - Request formal package review
   - Submit to official Fedora repositories

4. **Expand architecture support**
   - Test on aarch64 (ARM)
   - Test on s390x (IBM mainframe)
   - Test on ppc64le (POWER)

5. **Integrate with related packages**
   - Package Attestation Service
   - Package Key Broker Service
   - Create meta-package for full Trustee stack

---

## References

- **RVPS Packaging Analysis:** [dependencies-rvps.md](dependencies-rvps.md)
- **Copr Documentation:** https://docs.pagure.org/copr.copr/
- **Fedora Packaging Guidelines:** https://docs.fedoraproject.org/en-US/packaging-guidelines/
- **Fedora Rust Packaging:** https://docs.fedoraproject.org/en-US/packaging-guidelines/Rust/
- **RPM Packaging Guide:** https://rpm-packaging-guide.github.io/
- **Mock Documentation:** https://github.com/rpm-software-management/mock/wiki
- **Systemd Service Hardening:** https://www.freedesktop.org/software/systemd/man/systemd.exec.html

---

**Last Updated:** 2025-10-15
**Maintainer:** Your Name <your.email@example.com>
