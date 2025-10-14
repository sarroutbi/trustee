Name:           trustee-rvps
Version:        0.1.0
Release:        1%{?dist}
Summary:        Reference Value Provider Service for Trustee

License:        Apache-2.0
URL:            https://github.com/confidential-containers/trustee
Source0:        https://github.com/confidential-containers/trustee/archive/refs/heads/main.tar.gz#/trustee-%{version}.tar.gz

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
%autosetup -n trustee-main

%build
cd rvps
# Build with online dependency resolution (no vendoring)
# NOTE: Requires Copr build to have network access enabled
cargo build --release --locked

%install
# Install binaries
install -D -m 0755 target/release/rvps %{buildroot}%{_bindir}/rvps
install -D -m 0755 target/release/rvps-tool %{buildroot}%{_bindir}/rvps-tool

# Install systemd unit
install -d -m 0755 %{buildroot}%{_unitdir}
cat >%{buildroot}%{_unitdir}/trustee-rvps.service <<EOF
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
EOF

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

%check
cd rvps
# Run tests with verbose output
# --nocapture shows stdout/stderr from tests
# --test-threads=1 runs tests serially for clearer output
cargo test --release -- --nocapture --test-threads=1

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
* Wed Oct 15 2025 Sergio Arroutbi <sarroutb@redhat.com> - 0.1.0-1
- Initial package for Fedora 42
- Build without vendoring (using online dependency resolution)
- Based on main branch from upstream
- Standalone RVPS service with gRPC API (port 50003)
