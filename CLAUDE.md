# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Trustee provides tools and components for attesting confidential guests and providing secrets to them. It's designed for Confidential Containers but works with various applications and hardware platforms. The repository implements the RATS (Remote ATtestation procedureS) architecture with multiple deployment modes.

## Architecture

### Core Components

The repository consists of three main services that work together:

1. **Key Broker Service (KBS)** - `kbs/`
   - Acts as the Relying Party in RATS model
   - Facilitates remote attestation and secret delivery
   - Supports two operational modes:
     - **Background Check Mode**: KBS validates evidence via AS before releasing secrets (most common)
     - **Passport Mode**: Decouples evidence verification from resource provisioning using two KBS instances
   - Can integrate with attestation services via:
     - Built-in CoCo AS (compiled into binary)
     - Remote gRPC CoCo AS
     - Intel Trust Authority (SGX/TDX only)

2. **Attestation Service (AS)** - `attestation-service/`
   - Acts as the Verifier in RATS model
   - Verifies TEE (Trusted Execution Environment) evidence
   - Two-step verification:
     1. Verifier drivers validate evidence format and signature
     2. Policy engine (OPA) evaluates claims against reference values
   - Can be deployed as:
     - Rust crate/library
     - Standalone gRPC service (`grpc-as`)
     - Standalone REST service (`restful-as`)
   - Outputs attestation results as JWT tokens

3. **Reference Value Provider Service (RVPS)** - `rvps/`
   - Receives and verifies software supply chain provenances
   - Stores reference values for evidence comparison
   - Can run in two modes:
     - Native mode (crate inside AS binary)
     - gRPC mode (remote service)

### Supporting Components

- **Verifier Drivers** - `deps/verifier/`
  - Platform-specific evidence verification for: TDX, SGX, SNP, CCA, CSV, Azure vTPM (SNP/TDX), IBM SE, NVIDIA, TPM
  - Feature flags control which verifiers are compiled (e.g., `tdx-verifier`, `snp-verifier`)

- **Event Log** - `deps/eventlog/`
  - Handles event log parsing and validation

- **KBS Client** - `tools/kbs-client/`
  - Rust SDK and CLI tool for interacting with KBS

- **Trustee CLI** - `tools/trustee/`
  - Unified command-line interface

- **Integration Tests** - `integration-tests/`
  - End-to-end testing across components

## Build Commands

### Building Workspace

All components are in a Cargo workspace. Build everything from repository root:

```bash
cargo build --release
```

### KBS (Key Broker Service)

The KBS supports multiple build configurations via Makefiles in `kbs/`:

```bash
# Background check mode with built-in AS (most common)
make -C kbs background-check-kbs

# With specific AS type
make -C kbs background-check-kbs AS_TYPE=coco-as COCO_AS_INTEGRATION_TYPE=builtin

# With remote gRPC AS
make -C kbs background-check-kbs COCO_AS_INTEGRATION_TYPE=grpc

# Passport mode variants
make -C kbs passport-issuer-kbs
make -C kbs passport-resource-kbs

# Build KBS client CLI
make -C kbs cli

# Cross-compilation (Debian-like systems only)
make -C kbs background-check-kbs ARCH=aarch64
```

**Build Parameters:**
- `AS_TYPE`: `coco-as` (default) or `intel-trust-authority-as`
- `COCO_AS_INTEGRATION_TYPE`: `builtin` (AS as crate) or `grpc` (remote AS)
- `ALIYUN`: `true` to enable Aliyun KMS backend
- `NEBULA_CA_PLUGIN`: `true` to enable Nebula CA plugin
- `VAULT`: `true` to enable Vault storage backend
- `ARCH`: Target architecture for cross-compilation

### Attestation Service

Build AS binaries from `attestation-service/`:

```bash
# Build both gRPC and RESTful AS
make -C attestation-service build

# Build specific variant
make -C attestation-service grpc-as
make -C attestation-service restful-as

# With specific verifier (default is all-verifier)
make -C attestation-service grpc-as VERIFIER=tdx-verifier

# Enable remote RVPS (default is builtin)
make -C attestation-service grpc-as RVPS_GRPC=true
```

**Build Parameters:**
- `VERIFIER`: Specific verifier feature (e.g., `tdx-verifier`, `snp-verifier`, `all-verifier`)
- `RVPS_GRPC`: `true` to connect to remote RVPS, `false` for built-in
- `DEBUG`: Set to build debug version instead of release

### RVPS

```bash
# Build and install RVPS
cd rvps
make build && sudo make install

# RVPS runs on localhost:50003 by default
rvps --address 127.0.0.1:50003
```

## Testing

### Unit and Integration Tests

```bash
# Test all workspace members
cargo test

# Test specific component
cargo test -p kbs
cargo test -p attestation-service
cargo test -p rvps

# Test with specific features
cargo test -p kbs --no-default-features --features coco-as-builtin

# Run integration tests
cargo test -p integration-tests

# KBS-specific tests
make -C kbs check

# Test with specific feature set
make -C kbs check TEST_FEATURES="coco-as-builtin,resource"
```

### E2E Tests

```bash
# Attestation Service E2E tests
make -C attestation-service/tests/e2e

# KBS E2E tests (requires Docker)
# See kbs/test/ for test scripts
```

### Running Single Test

```bash
# Run single test by name
cargo test -p kbs test_name

# Run with output
cargo test -p kbs test_name -- --nocapture

# Run tests matching pattern
cargo test -p attestation-service token
```

## Linting and Formatting

```bash
# Lint entire workspace
cargo clippy --all-targets -- -D warnings

# Lint specific component
make -C kbs lint
cargo clippy -p attestation-service -- -D warnings

# Format check
make -C kbs format
cargo fmt --all -- --check --config format_code_in_doc_comments=true

# Apply formatting
cargo fmt --all

# Validate OPA policies (attestation-service only)
make -C attestation-service opa-check
```

## Running Services Locally

### Using Docker Compose

Easiest way to run complete cluster:

```bash
# See kbs/docs/cluster.md for setup
docker-compose up
```

### Running Individual Services

**KBS:**
```bash
./target/release/kbs --config-file kbs/config.toml
# Or via environment: KBS_CONFIG_FILE=config.toml ./target/release/kbs
```

**Attestation Service (gRPC):**
```bash
./target/release/grpc-as --config-file attestation-service/config.json
# Listens on 127.0.0.1:50004 by default
```

**Attestation Service (RESTful):**
```bash
./target/release/restful-as --config-file attestation-service/config.json
```

**RVPS:**
```bash
rvps --address 127.0.0.1:50003
# With config: rvps -c rvps/config.json
```

## Configuration Files

### KBS Configuration

- Format: TOML (also supports JSON, YAML)
- Location: Passed via `-c/--config-file` or `KBS_CONFIG_FILE` env var
- Key sections:
  - `[http_server]`: Sockets, TLS settings
  - `[attestation_service]`: AS type and connection details
  - `[attestation_token]`: Token verification settings
  - `[[plugins]]`: Resource storage, Nebula CA, etc.
- Examples: See `kbs/docs/config.md`

### AS Configuration

- Format: JSON
- Location: Passed via `--config-file`
- Key properties:
  - `work_dir`: Data storage location (default: `/opt/confidential-containers/attestation-service`)
  - `rvps_config`: RVPS mode and settings
  - `attestation_token_broker`: Token signing and duration
- Examples: See `attestation-service/docs/config.md`

### RVPS Configuration

- Format: JSON
- Key properties:
  - `storage.type`: `LocalFs` or `LocalJson`
  - `storage.file_path`: Where to store reference values

## Key Architectural Patterns

### Feature Flag System

The codebase uses extensive Cargo feature flags to control which components are compiled:

- **Verifiers**: Each TEE platform is a separate feature (e.g., `tdx-verifier`, `snp-verifier`)
- **AS Integration**: `coco-as-builtin` vs `coco-as-grpc` determines if AS is compiled in or remote
- **Storage Backends**: `aliyun`, `vault` enable cloud KMS backends
- **Plugins**: `nebula-ca-plugin` for Nebula CA functionality

When modifying code, be aware that features control conditional compilation. Test with relevant feature combinations.

### Integration Modes

Understanding the AS integration modes is critical:

1. **Built-in AS** (`coco-as-builtin`): AS compiled as crate into KBS binary. Simpler deployment but tightly coupled.
2. **gRPC AS** (`coco-as-grpc`): KBS connects to remote AS via gRPC. Enables separate scaling and policy management.
3. **Intel TA** (`intel-trust-authority-as`): KBS connects to Intel Trust Authority cloud service.

The mode affects which configuration fields are valid and how errors propagate.

### Policy Engine

Attestation Service uses OPA (Open Policy Agent) with Rego policies:
- Default policy: `attestation-service/src/token/ear_default_policy_cpu.rego`
- Custom policies can be uploaded and selected via `policy_ids` in attestation requests
- Policy evaluation results are included in attestation tokens
- When modifying policies, validate with `make opa-check`

### Token Format

AS outputs attestation results as JWT tokens containing:
- `tcb-status`: Hardware and software measurements
- `evaluation-reports`: OPA policy evaluation results
- `reference-data`: Reference values used for verification
- `customized_claims`: Runtime data bound to evidence

KBS verifies these tokens before releasing resources.

## Development Workflow

### Verifier Development

When adding/modifying TEE verifiers:
1. Code lives in `deps/verifier/src/<platform>/`
2. Add feature flag in `deps/verifier/Cargo.toml`
3. Include in `all-verifier` feature
4. Update platform list in `attestation-service/README.md`
5. Add test data to `deps/verifier/test_data/<platform>/`

### Testing Changes

For KBS changes:
```bash
# Build with your features
make -C kbs background-check-kbs AS_TYPE=coco-as COCO_AS_INTEGRATION_TYPE=builtin

# Run tests with same features
make -C kbs check TEST_FEATURES="coco-as-builtin,resource"

# Lint
make -C kbs lint format
```

For AS changes:
```bash
# Build both interfaces
make -C attestation-service build

# Test
cargo test -p attestation-service

# Validate policies if modified
make -C attestation-service opa-check
```

## Common Gotchas

1. **Cross-compilation**: Only tested on Debian-like systems. Requires `gcc-<arch>-linux-gnu` and OpenSSL dev libraries for target arch.

2. **Feature combinations**: Not all feature combinations are valid. For example, `coco-as-builtin` and `coco-as-grpc` are mutually exclusive.

3. **OpenSSL on UBI**: When building for RHEL/UBI images, OpenSSL compilation may require special handling (see recent commits for fixes).

4. **Work directories**: AS and KBS have default work directories in `/opt/confidential-containers/`. Ensure proper permissions or override in config for local development.

5. **gRPC port conflicts**: Default ports are:
   - AS gRPC: `50004`
   - RVPS gRPC: `50003`
   - KBS HTTP: `8080`

6. **Test isolation**: Some tests require `serial_test` annotation as they modify shared state or use fixed ports.

## Documentation References

- KBS: `kbs/README.md`, `kbs/docs/`
- AS: `attestation-service/README.md`, `attestation-service/docs/`
- RVPS: `rvps/README.md`
- API specs: `kbs/docs/kbs.yaml` (OpenAPI 3.1)
- Attestation protocol: `kbs/docs/kbs_attestation_protocol.md`
- Cluster setup: `kbs/docs/cluster.md`
