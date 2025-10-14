#!/usr/bin/env python3
"""
Fedora Package Availability Checker

This script parses Trustee dependency markdown files and verifies that all
listed packages exist in Fedora repositories by querying src.fedoraproject.org.

The script automatically maps binary package names (e.g., protobuf-compiler,
libgcc) to their source package names (e.g., protobuf, gcc) since
src.fedoraproject.org uses source package names.

Usage:
    ./check-fedora-packages.py dependencies-rvps.md
    ./check-fedora-packages.py dependencies-analysis.md --verbose
"""

import argparse
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests


@dataclass
class Package:
    """Represents a package dependency"""
    name: str
    required_version: str
    fedora_version: str
    category: str  # 'build' or 'runtime'

    def __str__(self):
        return f"{self.name} (required: {self.required_version}, Fedora: {self.fedora_version})"


class FedoraPackageChecker:
    """Checks package availability in Fedora repositories"""

    BASE_URL = "https://src.fedoraproject.org"
    RPMS_URL = f"{BASE_URL}/rpms/"

    # Mapping of binary package names to source package names
    # src.fedoraproject.org uses source package names
    BINARY_TO_SOURCE = {
        'protobuf-compiler': 'protobuf',
        'libgcc': 'gcc',
        'openssl-devel': 'openssl',
        'openssl-libs': 'openssl',
        'pkg-config': 'pkgconf',
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Trustee-Dependency-Checker/1.0'
        })

    def check_package_exists(self, package_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a package exists in Fedora src repository.

        Returns:
            (exists, url) tuple where exists is True if package found,
            and url is the package URL if it exists
        """
        # Map binary package name to source package name if needed
        source_pkg_name = self.BINARY_TO_SOURCE.get(package_name, package_name)
        package_url = urljoin(self.RPMS_URL, source_pkg_name)

        if self.verbose and source_pkg_name != package_name:
            print(f"  Note: {package_name} → {source_pkg_name} (source package)")

        try:
            response = self.session.get(package_url, timeout=10, allow_redirects=True)

            if response.status_code == 200:
                # Check if we got a valid package page (not a 404 page)
                if "Project not found" in response.text or "Page not found" in response.text:
                    return False, None
                return True, package_url
            if response.status_code == 404:
                return False, None
            if self.verbose:
                print(f"Warning: Unexpected status {response.status_code} "
                      f"for {package_name}")
            return False, None

        except requests.exceptions.RequestException as e:
            if self.verbose:
                print(f"Error checking {package_name}: {e}")
            return False, None

    def parse_markdown_table(self, content: str) -> List[Package]:
        """
        Parse markdown dependency tables and extract package information.

        Looks for tables with columns:
        - Dependency
        - Required Version
        - Available in Fedora 42
        """
        packages = []
        lines = content.split('\n')
        current_category = None

        for line in lines:
            # Detect section headers
            if ('## 2. Build Dependencies' in line or
                    '## 3. Build Dependencies' in line):
                current_category = 'build'
                continue
            if '## 4. Runtime Dependencies' in line:
                current_category = 'runtime'
                continue
            if line.startswith('## ') and current_category:
                # End of dependency sections
                if 'Dependencies' not in line:
                    current_category = None
                continue

            # Skip if not in a dependency section
            if not current_category:
                continue

            # Parse table rows
            if not (line.strip().startswith('|') and '|' in line):
                continue

            # Skip header and separator rows
            if ('Dependency' in line or 'Required Version' in line or
                    re.match(r'^\|\s*[-:]+\s*\|', line)):
                continue

            # Parse data row
            parts = [p.strip() for p in line.split('|') if p.strip()]

            if len(parts) < 3:
                continue

            dep_name = parts[0].strip('`').strip()
            required_ver = parts[1].strip()
            fedora_ver = parts[2].strip()

            # Skip empty rows or continuation rows
            if not dep_name or dep_name == '...' or not required_ver:
                continue

            # Extract version from strings like "✅ Yes (1.90.0)"
            fedora_version_match = re.search(r'\(([^)]+)\)', fedora_ver)
            fedora_version = (fedora_version_match.group(1)
                              if fedora_version_match else fedora_ver)

            packages.append(Package(
                name=dep_name,
                required_version=required_ver,
                fedora_version=fedora_version,
                category=current_category
            ))

        return packages

    def verify_packages(self, packages: List[Package]) -> Dict[str, any]:
        """
        Verify all packages exist in Fedora repositories.

        Returns:
            Dictionary with verification results
        """
        results = {
            'total': len(packages),
            'found': 0,
            'not_found': 0,
            'packages': {
                'build': {'found': [], 'not_found': []},
                'runtime': {'found': [], 'not_found': []}
            }
        }

        print(f"\nChecking {len(packages)} packages in Fedora repositories...\n")

        for pkg in packages:
            exists, url = self.check_package_exists(pkg.name)

            if exists:
                results['found'] += 1
                results['packages'][pkg.category]['found'].append((pkg, url))
                status = "✅ FOUND"
            else:
                results['not_found'] += 1
                results['packages'][pkg.category]['not_found'].append(pkg)
                status = "❌ NOT FOUND"

            print(f"{status:15} {pkg.name:25} (Fedora: {pkg.fedora_version})")
            if exists and url and self.verbose:
                print(f"               → {url}")

        return results

    def print_summary(self, results: Dict[str, any]):
        """Print a summary of verification results"""
        print("\n" + "="*80)
        print("VERIFICATION SUMMARY")
        print("="*80)

        for category in ['build', 'runtime']:
            cat_name = category.upper()
            found = results['packages'][category]['found']
            not_found = results['packages'][category]['not_found']

            print(f"\n{cat_name} DEPENDENCIES:")
            print(f"  Found:     {len(found)}")
            print(f"  Not Found: {len(not_found)}")

            if not_found:
                print(f"\n  Missing {cat_name} packages:")
                for pkg in not_found:
                    print(f"    - {pkg.name} (required: {pkg.required_version})")

        print(f"\nTOTAL: {results['found']}/{results['total']} "
              "packages found in Fedora")

        if results['not_found'] == 0:
            print("\n✅ SUCCESS: All packages are available in "
                  "Fedora repositories!")
            return True
        print(f"\n⚠️  WARNING: {results['not_found']} package(s) not found "
              "in Fedora repositories")
        return False


def main():
    """Main entry point for the Fedora package checker."""
    parser = argparse.ArgumentParser(
        description='Verify Fedora package availability from dependency '
                    'markdown files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s dependencies-rvps.md
  %(prog)s dependencies-analysis.md --verbose
  %(prog)s dependencies-rvps.md -v
        """
    )

    parser.add_argument(
        'markdown_file',
        help='Path to dependency markdown file to check'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output (show URLs)'
    )

    args = parser.parse_args()

    # Read markdown file
    try:
        with open(args.markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{args.markdown_file}' not found",
              file=sys.stderr)
        return 1
    except (IOError, OSError) as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    # Parse and verify packages
    checker = FedoraPackageChecker(verbose=args.verbose)

    print(f"Parsing dependency file: {args.markdown_file}")
    packages = checker.parse_markdown_table(content)

    if not packages:
        print("Warning: No packages found in markdown file")
        print("Make sure the file contains dependency tables with:")
        print("  - A 'Dependency' column")
        print("  - A 'Required Version' column")
        print("  - An 'Available in Fedora 42' column")
        return 1

    print(f"Found {len(packages)} packages to verify")

    # Verify packages
    results = checker.verify_packages(packages)

    # Print summary
    success = checker.print_summary(results)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
