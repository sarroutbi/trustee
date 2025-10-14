# Trustee Packaging Dependency Analysis

**Last Updated:** 2025-10-14
**Analyzed Version:** commit 42f5c66 (main branch)
**Target Distributions:** Fedora 42 and RHEL 10.2
**Analysis Scope:** Build and runtime dependencies for RPM packaging

## 1. Summary

This document provides a technical analysis of the Trustee project to prepare it for packaging as RPMs for Fedora 42 and future RHEL 10.2 distributions. Trustee is a suite of components (KBS, Attestation Service, RVPS) for remote attestation and secret management in confidential computing environments.

The project is a Rust-based workspace with three main components:
- **KBS (Key Broker Service)**: Resource provisioning with attestation
- **Attestation Service**: TEE evidence verification
- **RVPS (Reference Value Provider Service)**: Reference value management

All three components should be packaged as separate RPMs with their own binaries, libraries, and systemd services.

---

## 2. Build Dependencies

The following packages are required to build all Trustee components from source on Fedora 42.

### 2.1 Core Build Tools

| Dependency             | Required Version | Available in Fedora 42 | Available in RHEL 10.2 | Notes                                         |
| ---------------------- | ---------------- | ---------------------- | ---------------------- | --------------------------------------------- |
| `rust`                 | >= 1.70          | ✅ Yes (1.90.0)        | ✅ Likely (1.85+)      | The core Rust compiler. Fedora 42 ships 1.90. Current system has 1.85.1. |
| `cargo`                | >= 1.70          | ✅ Yes (1.90.0)        | ✅ Likely (1.85+)      | Rust's package manager and build tool.        |
| `gcc`                  | >= 7.0           | ✅ Yes (15.2.1)        | ✅ Yes                 | Required for linking and some native dependencies. |
| `make`                 | Any              | ✅ Yes (4.4.1)         | ✅ Yes                 | Build orchestration via Makefiles.            |
| `git`                  | Any              | ✅ Yes (2.51.0)        | ✅ Yes                 | Required for building (shadow-rs needs git info). |
| `pkg-config`           | Any              | ✅ Yes                 | ✅ Yes                 | For finding library dependencies.             |

### 2.2 System Libraries (Development Packages)

| Dependency             | Required Version | Available in Fedora 42 | Available in RHEL 10.2 | Notes                                         |
| ---------------------- | ---------------- | ---------------------- | ---------------------- | --------------------------------------------- |
| `openssl-devel`        | >= 3.0           | ✅ Yes (3.2.6)         | ✅ Yes (3.0.x)         | Needed for TLS, cryptographic functions. Critical dependency. |
| `protobuf-compiler`    | >= 3.19          | ✅ Yes (3.19.6)        | ⚠️ Maybe (3.19.x)      | **Important:** gRPC code generation. Fedora 42 has 3.19.6 which meets minimum. |

**Note on protobuf-compiler:** The workspace uses `tonic-build` (0.12) which requires protobuf >= 3.15. Fedora 42's 3.19.6 is sufficient. RHEL 10.2 should have a compatible version, but this needs verification.

### 2.3 Optional Build Dependencies

| Dependency             | Required For            | Available in Fedora 42 | Notes                                         |
| ---------------------- | ----------------------- | ---------------------- | --------------------------------------------- |
| `golang`               | RVPS `in-toto` feature  | ✅ Yes                 | Only needed if building with in-toto support (currently not default). |
| `clang`                | Some Rust dependencies  | ✅ Yes (20.1.8)        | Optional but recommended for better compilation of some crates. |

### 2.4 Rust Ecosystem Dependencies

All Rust dependencies are vendored via Cargo and do not require system packages. The main categories of Rust crates include:

- **Async Runtime:** `tokio` (v1), `actix-web` (v4)
- **Serialization:** `serde`, `serde_json`, `prost` (protobuf), `toml`
- **Cryptography:** `openssl`, `rsa`, `p256`, `sha2`, `aes-gcm`, `jwt-simple`, `jsonwebtoken`
- **gRPC:** `tonic` (v0.12), `tonic-build` (v0.12)
- **Policy Engine:** `regorus` (OPA/Rego implementation)
- **TEE Verification:** Platform-specific crates (most are pure Rust or link to `openssl`)

**Intel SGX/TDX Specific:** When building with `tdx-verifier` or `sgx-verifier` features, Cargo fetches `intel-tee-quote-verification-rs` from Intel's DCAP repository (tag DCAP_1.23). This is a Rust crate with C++ bindings.

---

## 3. Runtime Dependencies

The following packages are required to run the Trustee services after installation.

### 3.1 System Libraries (Runtime)

| Dependency             | Available in Fedora 42 | Available in RHEL 10.2 | Notes                               |
| ---------------------- | ---------------------- | ---------------------- | ----------------------------------- |
| `openssl-libs`         | ✅ Yes (3.2.6)         | ✅ Yes (3.0.x)         | Core SSL/TLS libraries. Critical runtime dependency. |
| `glibc`                | ✅ Yes (2.41)          | ✅ Yes (2.39+)         | Standard C library.                 |
| `libgcc`               | ✅ Yes                 | ✅ Yes                 | GCC runtime library.                |

### 3.2 Optional Runtime Dependencies

| Dependency             | Required For            | Available              | Notes                               |
| ---------------------- | ----------------------- | ---------------------- | ----------------------------------- |
| `systemd`              | Service management      | ✅ Yes                 | For running services via systemd units. |

**Important:** Trustee binaries are statically linked Rust executables. They have minimal runtime dependencies beyond glibc and openssl-libs. No Python, no Java, no Node.js required.

---

## 4. Upstream Source Code Analysis

### 4.1 Repository Information

- **Upstream Repository:** `https://github.com/confidential-containers/trustee`
- **Current Fork:** `https://github.com/sarroutbi/trustee` (appears to be a development fork)
- **Version Analyzed:** commit `42f5c66` from main branch
- **License:** Apache License 2.0 ✅ (Compatible with Fedora/RHEL)
- **Build System:** Cargo workspace with component-specific Makefiles
- **Language:** Rust (edition 2021)

### 4.2 Component Structure

The repository is organized as a Cargo workspace with the following components:

1. **kbs/** - Key Broker Service
   - Binary: `kbs` (or `issuer-kbs`/`resource-kbs` for passport mode)
   - Supports multiple AS integration modes (builtin, gRPC, Intel TA)

2. **attestation-service/** - Attestation Service
   - Binaries: `grpc-as`, `restful-as`
   - Can be used as library or standalone service

3. **rvps/** - Reference Value Provider Service
   - Binaries: `rvps`, `rvps-tool`
   - Standalone gRPC service or library

4. **tools/kbs-client/** - KBS Client
   - Binary: `kbs-client`
   - CLI tool and Rust SDK

5. **tools/trustee/** - Unified Trustee CLI
   - Binary: `trustee`

6. **deps/verifier/** - TEE Verifier Library
   - Library only, no binary

7. **deps/eventlog/** - Event Log Library
   - Library only, no binary

### 4.3 Build Process

The build process is clean and well-documented:

```bash
# Standard Cargo workspace build
cargo build --release

# Or via Makefiles for component-specific builds
make -C kbs background-check-kbs
make -C attestation-service grpc-as
make -C rvps build
```

**Build System Characteristics:**
- Uses standard Cargo with workspace dependencies
- Feature flags control which components are compiled
- Makefiles provide convenient wrappers around `cargo build`
- Build-time code generation via `build.rs` scripts (shadow-rs for version info, tonic-build for protobuf)
- Cross-compilation supported for aarch64, s390x (Debian-based systems only)

### 4.4 Configuration Management

**KBS Configuration:**
- Format: TOML (also supports JSON, YAML)
- Default location: Via `-c/--config-file` flag or `KBS_CONFIG_FILE` env var
- No hardcoded paths ✅
- Default work directory: `/opt/confidential-containers/kbs/`

**Attestation Service Configuration:**
- Format: JSON
- Default location: Via `--config-file` flag
- Default work directory: `/opt/confidential-containers/attestation-service/`
- Env var override: `AS_WORK_DIR`

**RVPS Configuration:**
- Format: JSON
- Default location: Via `-c` flag
- Default storage: `/opt/confidential-containers/attestation-service/reference_values`

**Assessment:** Configuration is well-designed for packaging. Paths can be overridden via config files and environment variables. No hardcoded paths in binaries ✅

---

## 5. Proposed Installation Layout (FHS Compliance)

### 5.1 Package: trustee-kbs

**Binary:**
- `/usr/bin/kbs`

**Systemd Units:**
- `/usr/lib/systemd/system/trustee-kbs.service`

**Configuration:**
- `/etc/trustee/kbs.toml` (default configuration)
- `/etc/trustee/kbs-policy.rego` (default OPA policy)

**Data Directories:**
- `/var/lib/trustee/kbs/` (runtime data)
- `/var/lib/trustee/kbs/repository/` (resource storage for LocalFs backend)

**Log Directory:**
- Logs to systemd journal (no dedicated log directory needed)

**Documentation:**
- `/usr/share/doc/trustee-kbs/README.md`
- `/usr/share/doc/trustee-kbs/examples/`

---

### 5.2 Package: trustee-attestation-service

**Binaries:**
- `/usr/bin/grpc-as`
- `/usr/bin/restful-as`

**Systemd Units:**
- `/usr/lib/systemd/system/trustee-grpc-as.service`
- `/usr/lib/systemd/system/trustee-restful-as.service`

**Configuration:**
- `/etc/trustee/attestation-service.json`

**Data Directories:**
- `/var/lib/trustee/attestation-service/` (work directory)
- `/var/lib/trustee/attestation-service/reference_values/` (if using built-in RVPS)
- `/var/lib/trustee/attestation-service/token/` (policy storage)

**Documentation:**
- `/usr/share/doc/trustee-attestation-service/README.md`
- `/usr/share/doc/trustee-attestation-service/docs/`

---

### 5.3 Package: trustee-rvps

**Binaries:**
- `/usr/bin/rvps`
- `/usr/bin/rvps-tool`

**Systemd Units:**
- `/usr/lib/systemd/system/trustee-rvps.service`

**Configuration:**
- `/etc/trustee/rvps.json`

**Data Directories:**
- `/var/lib/trustee/rvps/` (storage directory)

**Documentation:**
- `/usr/share/doc/trustee-rvps/README.md`

---

### 5.4 Package: trustee-client (or kbs-client)

**Binary:**
- `/usr/bin/kbs-client`

**Documentation:**
- `/usr/share/doc/trustee-client/README.md`

**No systemd service** (client tool only)

---

### 5.5 Shared Package: trustee-common (optional)

Could contain:
- Common documentation
- License file
- Shared configuration templates

---

## 6. Feature Flags and Build Variants

Trustee uses extensive Cargo feature flags. The following build configurations should be considered:

### 6.1 KBS Build Variants

**Default (Recommended for Fedora):**
```bash
make -C kbs background-check-kbs \
  AS_TYPE=coco-as \
  COCO_AS_INTEGRATION_TYPE=builtin
```

Features: `coco-as-builtin` (includes all TEE verifiers)

**Alternative: gRPC AS Integration**
```bash
make -C kbs background-check-kbs \
  COCO_AS_INTEGRATION_TYPE=grpc
```

Features: `coco-as-grpc` (connects to remote AS)

**Intel Trust Authority Variant:**
```bash
make -C kbs background-check-kbs \
  AS_TYPE=intel-trust-authority-as
```

Features: `intel-trust-authority-as` (for Intel SGX/TDX only)

**Optional Storage Backends:**
- `ALIYUN=true` → Enables Aliyun KMS support
- `VAULT=true` → Enables HashiCorp Vault support
- `NEBULA_CA_PLUGIN=true` → Enables Nebula CA plugin

### 6.2 Attestation Service Build Variants

**Default (All Verifiers):**
```bash
make -C attestation-service build \
  VERIFIER=all-verifier \
  RVPS_GRPC=true
```

Features: `grpc-bin`, `restful-bin`, `all-verifier`, `rvps-grpc`

**Architecture-Specific Builds:**
- **x86_64:** Include `tdx-verifier`, `sgx-verifier`, `snp-verifier`, `az-snp-vtpm-verifier`, `az-tdx-vtpm-verifier`, `csv-verifier`, `nvidia-verifier`, `tpm-verifier`
- **s390x:** Only `se-verifier` (IBM Secure Execution)
- **aarch64:** Only `cca-verifier` (ARM CCA)

**Recommendation:** Build separate packages for different architectures with appropriate verifier sets.

### 6.3 RVPS Build

**Standard Build:**
```bash
make -C rvps build
```

Features: `bin` (default)

**With in-toto support (optional):**
Requires golang for CGO bindings. Not recommended for standard package.

---

## 7. Risks and Considerations

### 7.1 Build-Time Risks

1. **Protobuf Compiler Version**
   - **Risk Level:** Low ⚠️
   - **Issue:** Fedora 42 ships protobuf-compiler 3.19.6. RHEL 10.2 likely has similar version.
   - **Mitigation:** This version meets the minimum requirement (tonic-build 0.12 needs >= 3.15). Should work without issues.

2. **Intel DCAP Dependencies**
   - **Risk Level:** Medium ⚠️
   - **Issue:** When building with Intel TDX/SGX verifiers, Cargo fetches `intel-tee-quote-verification-rs` from GitHub (DCAP_1.23 tag). This is a Rust wrapper around Intel's C++ DCAP libraries.
   - **Mitigation:**
     - For standard builds: Use `all-verifier` which includes these features.
     - For offline/vendored builds: Need to vendor this git dependency.
     - Intel DCAP libraries themselves are not required at build time (only Rust bindings).

3. **Cross-Compilation Limitations**
   - **Risk Level:** Low ℹ️
   - **Issue:** Cross-compilation is only tested on Debian-like systems per Makefiles.
   - **Mitigation:** For Fedora/RHEL, build natively on each target architecture. ExclusiveArch in spec file.

4. **Network Access During Build**
   - **Risk Level:** High for Mock/Koji 🔴
   - **Issue:** Standard `cargo build` downloads crates from crates.io.
   - **Mitigation:** **MUST vendor all dependencies** using `cargo vendor` before packaging. This is standard practice for Fedora Rust packages.

### 7.2 Runtime Risks

1. **OpenSSL Version Compatibility**
   - **Risk Level:** Low ✅
   - **Issue:** Code uses `openssl` crate which binds to system OpenSSL.
   - **Current Status:** Works with OpenSSL 3.2.6 (Fedora 42), should work with OpenSSL 3.0.x (RHEL 10.2).
   - **Mitigation:** Test runtime on both Fedora 42 and RHEL 10.2 beta.

2. **gRPC Port Conflicts**
   - **Risk Level:** Low ℹ️
   - **Issue:** Default ports might conflict with other services:
     - KBS: 8080 (HTTP)
     - AS gRPC: 50004
     - RVPS: 50003
   - **Mitigation:** Document default ports, provide config file examples with different ports.

3. **File Permissions and SELinux**
   - **Risk Level:** Medium ⚠️
   - **Issue:** Services write to `/var/lib/trustee/`, need correct permissions and SELinux contexts.
   - **Mitigation:**
     - Create `trustee` system user and group in `%pre` scriptlet
     - Set ownership: `chown -R trustee:trustee /var/lib/trustee/`
     - SELinux policy: May need custom policy for file contexts and network ports.

4. **Systemd Service Configuration**
   - **Risk Level:** Low ℹ️
   - **Issue:** Services should run as non-root user.
   - **Mitigation:**
     - `User=trustee` in systemd units
     - `DynamicUser=true` could be used but may complicate permissions
     - Recommended: Static UID/GID for `trustee` user

### 7.3 Packaging Risks

1. **Large Binary Sizes**
   - **Risk Level:** Low ℹ️
   - **Issue:** Rust binaries can be large (10-50 MB each). Release builds with all verifiers may exceed 100 MB.
   - **Mitigation:**
     - Split into multiple packages (already planned)
     - Strip debug symbols (default in Rust release builds)
     - Consider `opt-level = 's'` or `opt-level = 'z'` in Cargo.toml for size optimization

2. **Dependency Vendoring**
   - **Risk Level:** Medium ⚠️
   - **Issue:** Vendoring 200+ Rust crates significantly increases SRPM size.
   - **Mitigation:**
     - Standard practice for Fedora Rust packages
     - Use `rust2rpm` tooling
     - Document vendoring process in spec file

3. **Update Cadence**
   - **Risk Level:** Medium ⚠️
   - **Issue:** Trustee is under active development. Upstream releases may be frequent.
   - **Mitigation:**
     - Track upstream releases
     - Subscribe to confidential-containers mailing list
     - Use git tags for stable releases (currently upstream uses commit-based versioning)

---

## 8. Open Questions

1. **User and Group Creation:**
   - **Question:** Should all three services run as the same `trustee` user, or separate users (`trustee-kbs`, `trustee-as`, `trustee-rvps`)?
   - **Recommendation:** Single `trustee` user for simplicity, unless security policy requires separation.

2. **SELinux Policy:**
   - **Question:** Is a custom SELinux policy needed, or can we use standard contexts?
   - **Action Required:** Test on SELinux-enforcing Fedora 42 system.

3. **Systemd Hardening:**
   - **Question:** What systemd sandboxing options should be enabled?
   - **Recommendations:**
     - `NoNewPrivileges=true`
     - `PrivateTmp=true`
     - `ProtectSystem=strict`
     - `ProtectHome=true`
     - `ReadWritePaths=/var/lib/trustee/`

4. **Configuration File Format:**
   - **Question:** Should we standardize on TOML or JSON for all components?
   - **Current State:** KBS uses TOML, AS/RVPS use JSON.
   - **Recommendation:** Keep upstream defaults, document both in examples.

5. **Integration with CoCo Guest Components:**
   - **Question:** Are there dependencies on `guest-components` repository?
   - **Current State:** KBS depends on `kbs_protocol` and `kms` crates from `guest-components` (git dependency, rev 841b77f).
   - **Action Required:** These may need to be packaged separately or vendored.

6. **RHEL 10.2 Availability:**
   - **Question:** What is the target timeline for RHEL 10.2 support?
   - **Action Required:** Verify protobuf-compiler version in RHEL 10.2 beta when available.

7. **Architecture Support:**
   - **Question:** Which architectures should be supported in Fedora 42?
   - **Recommendation:**
     - `x86_64`: Full support (all verifiers)
     - `aarch64`: Limited support (CCA verifier only)
     - `s390x`: Limited support (SE verifier only)
     - `ppc64le`: Not applicable (no TEE support in upstream)

8. **Intel SGX/TDX Platform Requirements:**
   - **Question:** Do Intel verifiers require specific hardware or kernel modules at runtime?
   - **Current Understanding:** Verification can happen on any system; actual attestation requires TEE hardware.
   - **Action Required:** Clarify runtime requirements for Intel verifiers.

---

## 9. Recommended Packaging Strategy

### 9.1 Package Split

Create the following binary RPMs:

1. **trustee-kbs** - Key Broker Service
   - `Requires: openssl-libs, trustee-common`
   - `Recommends: trustee-attestation-service` (if using built-in AS)

2. **trustee-attestation-service** - Attestation Service
   - `Requires: openssl-libs, trustee-common`
   - `Recommends: trustee-rvps` (if using built-in RVPS)

3. **trustee-rvps** - Reference Value Provider Service
   - `Requires: openssl-libs, trustee-common`

4. **trustee-client** - KBS Client CLI
   - `Requires: openssl-libs`

5. **trustee-common** - Common files and documentation
   - License, shared docs

### 9.2 Build Process

```bash
# Vendor dependencies
cargo vendor

# Build all components
cargo build --release --all-targets

# Or use Makefiles
make -C kbs background-check-kbs AS_TYPE=coco-as COCO_AS_INTEGRATION_TYPE=builtin
make -C attestation-service build VERIFIER=all-verifier RVPS_GRPC=true
make -C rvps build
make -C tools/kbs-client cli
```

### 9.3 Spec File Structure

```spec
Name:           trustee
Version:        0.1.0
Release:        1%{?dist}
Summary:        Trusted components for attestation and secret management

License:        Apache-2.0
URL:            https://github.com/confidential-containers/trustee
Source0:        %{name}-%{version}.tar.gz
Source1:        vendor.tar.gz

BuildRequires:  rust >= 1.70
BuildRequires:  cargo >= 1.70
BuildRequires:  gcc
BuildRequires:  openssl-devel >= 3.0
BuildRequires:  protobuf-compiler >= 3.15
BuildRequires:  pkg-config
BuildRequires:  systemd-rpm-macros

# Architecture restrictions based on TEE support
ExclusiveArch:  x86_64 aarch64 s390x

%description
Trustee provides tools and components for attesting confidential guests
and providing secrets to them in confidential computing environments.

# ... subpackages ...

%prep
%autosetup -p1
%cargo_prep -v vendor

%build
# Build KBS
%make_build -C kbs background-check-kbs \
    AS_TYPE=coco-as \
    COCO_AS_INTEGRATION_TYPE=builtin

# Build Attestation Service
%make_build -C attestation-service build

# Build RVPS
%make_build -C rvps build

# Build Client
%make_build -C tools/kbs-client cli

%install
# Install binaries
install -D -m 0755 target/release/kbs %{buildroot}%{_bindir}/kbs
install -D -m 0755 target/release/grpc-as %{buildroot}%{_bindir}/grpc-as
install -D -m 0755 target/release/restful-as %{buildroot}%{_bindir}/restful-as
install -D -m 0755 target/release/rvps %{buildroot}%{_bindir}/rvps
install -D -m 0755 target/release/kbs-client %{buildroot}%{_bindir}/kbs-client

# Install systemd units
install -D -m 0644 %{SOURCE2} %{buildroot}%{_unitdir}/trustee-kbs.service
# ... etc ...

# Create data directories
install -d -m 0750 %{buildroot}%{_sharedstatedir}/trustee/kbs
install -d -m 0750 %{buildroot}%{_sharedstatedir}/trustee/attestation-service
install -d -m 0750 %{buildroot}%{_sharedstatedir}/trustee/rvps

%pre kbs
getent group trustee >/dev/null || groupadd -r trustee
getent passwd trustee >/dev/null || \
    useradd -r -g trustee -d %{_sharedstatedir}/trustee -s /sbin/nologin \
    -c "Trustee service account" trustee
exit 0

%post kbs
%systemd_post trustee-kbs.service

%preun kbs
%systemd_preun trustee-kbs.service

%postun kbs
%systemd_postun_with_restart trustee-kbs.service

%files kbs
%license LICENSE
%{_bindir}/kbs
%{_unitdir}/trustee-kbs.service
%dir %attr(0750,trustee,trustee) %{_sharedstatedir}/trustee/kbs
%config(noreplace) %{_sysconfdir}/trustee/kbs.toml

# ... similar for other subpackages ...
```

---

## 10. Testing Checklist

Before submitting packages to Fedora:

- [ ] Build succeeds on x86_64, aarch64, s390x in mock
- [ ] All binaries execute without errors (`--version`, `--help`)
- [ ] Systemd services start successfully
- [ ] SELinux denials checked and resolved
- [ ] File permissions and ownership correct in `/var/lib/trustee/`
- [ ] Configuration files parsed correctly
- [ ] Services communicate over expected ports
- [ ] Basic attestation flow works (KBS ↔ AS ↔ RVPS)
- [ ] Restart services without data loss
- [ ] Package upgrades work correctly
- [ ] Uninstall cleans up properly (except data in `/var/lib/`)
- [ ] License compliance verified (FOSS review)
- [ ] Documentation accurate and complete

---

## 11. References

- **Upstream Repository:** https://github.com/confidential-containers/trustee
- **Fedora Rust Packaging Guidelines:** https://docs.fedoraproject.org/en-US/packaging-guidelines/Rust/
- **Confidential Containers Documentation:** https://github.com/confidential-containers/documentation
- **RATS Architecture:** https://www.ietf.org/archive/id/draft-ietf-rats-architecture-22.html
- **Trustee KBS Documentation:** See `kbs/README.md` and `kbs/docs/` in repository
- **Attestation Service Documentation:** See `attestation-service/README.md` and `attestation-service/docs/`
- **RVPS Documentation:** See `rvps/README.md`

---

## 12. Changelog

| Date       | Changes                                      |
| ---------- | -------------------------------------------- |
| 2025-10-14 | Initial dependency analysis for Fedora 42 and RHEL 10.2 |

---

**End of Document**
