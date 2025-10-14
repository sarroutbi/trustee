#!/bin/bash
cp trustee-0.1.0.tar.gz ~/rpmbuild/SOURCES/
cp trustee-rvps-fedora-crates.spec ~/rpmbuild/SPECS/trustee-rvps.spec
pushd ~/rpmbuild/SPECS/
rpmbuild -bs trustee-rvps.spec
cp -v ~/rpmbuild/SRPMS/trustee-rvps-0.1.0-1.fc42.src.rpm ~/tmp/
popd
