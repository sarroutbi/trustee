#!/usr/bin/env python3
"""
RHEL Package Availability Checker

This script parses Trustee dependency markdown files and verifies that all
listed packages exist in RHEL 10.2 repositories by SSH'ing to a RHEL system
and querying dnf.

The script automatically maps binary package names (e.g., protobuf-compiler,
libgcc) to their source package names when needed.

Usage:
    ./check-rhel-packages.py dependencies-rvps.md --host 10.0.184.129
    ./check-rhel-packages.py dependencies-analysis.md --host 10.0.184.129 --verbose
    ./check-rhel-packages.py dependencies-rvps.md --host 10.0.184.129 --user myuser
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Package:
    """Represents a package dependency"""
    name: str
    required_version: str
    rhel_version: str
    category: str  # 'build' or 'runtime'

    def __str__(self):
        return (f"{self.name} (required: {self.required_version}, "
                f"RHEL: {self.rhel_version})")


class RHELPackageChecker:
    """Checks package availability in RHEL repositories via SSH"""

    # Mapping of binary package names to package names that dnf recognizes
    # Most binary packages work directly, but some need mapping
    PACKAGE_ALIASES = {
        'pkg-config': 'pkgconf',  # pkg-config is provided by pkgconf
    }

    def __init__(self, host: str, user: str = "root", verbose: bool = False):
        self.host = host
        self.user = user
        self.verbose = verbose

    def check_package_exists(self, package_name: str) -> Tuple[bool,
                                                                Optional[str]]:
        """
        Check if a package exists in RHEL repositories via SSH.

        Returns:
            (exists, version) tuple where exists is True if package found,
            and version is the package version if it exists
        """
        # Map package name if needed
        actual_pkg_name = self.PACKAGE_ALIASES.get(package_name, package_name)

        if self.verbose and actual_pkg_name != package_name:
            print(f"  Note: {package_name} → {actual_pkg_name} (alias)")

        # Build SSH command to check package
        ssh_cmd = [
            'ssh',
            f'{self.user}@{self.host}',
            f'dnf info --available {actual_pkg_name} 2>/dev/null | '
            f'grep -E "^(Name|Version)" | head -2'
        ]

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )

            if result.returncode == 0 and result.stdout.strip():
                # Parse output to get version
                version = self._parse_version_from_output(result.stdout)
                return True, version
            # Try checking installed packages
            ssh_cmd[2] = (f'dnf info --installed {actual_pkg_name} 2>/dev/null'
                          f' | grep -E "^(Name|Version)" | head -2')
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )

            if result.returncode == 0 and result.stdout.strip():
                version = self._parse_version_from_output(result.stdout)
                return True, version
            return False, None

        except subprocess.TimeoutExpired:
            if self.verbose:
                print(f"  Warning: Timeout checking {package_name}")
            return False, None
        except (subprocess.SubprocessError, OSError) as e:
            if self.verbose:
                print(f"  Error checking {package_name}: {e}")
            return False, None

    def _parse_version_from_output(self, output: str) -> str:
        """Parse version from dnf info output"""
        for line in output.split('\n'):
            if line.startswith('Version'):
                # Format: "Version      : 1.90.0"
                parts = line.split(':', 1)
                if len(parts) == 2:
                    return parts[1].strip()
        return "Unknown"

    def parse_markdown_table(self, content: str) -> List[Package]:
        """
        Parse markdown dependency tables and extract package information.

        Looks for tables with columns:
        - Dependency
        - Required Version
        - Available in RHEL 10.2
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

            # Need at least 4 columns for RHEL tables
            # (Dependency, Required, Fedora, RHEL)
            if len(parts) < 4:
                continue

            dep_name = parts[0].strip('`').strip()
            required_ver = parts[1].strip()
            rhel_ver = parts[3].strip()  # RHEL is 4th column

            # Skip empty rows or continuation rows
            if not dep_name or dep_name == '...' or not required_ver:
                continue

            # Extract version from strings like "✅ Yes (1.90.0)"
            rhel_version_match = re.search(r'\(([^)]+)\)', rhel_ver)
            rhel_version = (rhel_version_match.group(1)
                            if rhel_version_match else rhel_ver)

            packages.append(Package(
                name=dep_name,
                required_version=required_ver,
                rhel_version=rhel_version,
                category=current_category
            ))

        return packages

    def verify_packages(self, packages: List[Package]) -> Dict[str, any]:
        """
        Verify all packages exist in RHEL repositories.

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

        print(f"\nChecking {len(packages)} packages on RHEL system "
              f"{self.host}...\n")

        for pkg in packages:
            exists, version = self.check_package_exists(pkg.name)

            if exists:
                results['found'] += 1
                results['packages'][pkg.category]['found'].append(
                    (pkg, version)
                )
                status = "✅ FOUND"
                display_version = version if version else pkg.rhel_version
            else:
                results['not_found'] += 1
                results['packages'][pkg.category]['not_found'].append(pkg)
                status = "❌ NOT FOUND"
                display_version = pkg.rhel_version

            print(f"{status:15} {pkg.name:25} (RHEL: {display_version})")
            if exists and version and self.verbose:
                print(f"               → Verified version: {version}")

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
                    print(f"    - {pkg.name} "
                          f"(required: {pkg.required_version})")

        print(f"\nTOTAL: {results['found']}/{results['total']} "
              "packages found in RHEL 10.2")

        if results['not_found'] == 0:
            print("\n✅ SUCCESS: All packages are available in "
                  "RHEL 10.2 repositories!")
            return True
        print(f"\n⚠️  WARNING: {results['not_found']} package(s) not found "
              "in RHEL 10.2 repositories")
        return False


def main():
    """Main entry point for the RHEL package checker."""
    parser = argparse.ArgumentParser(
        description='Verify RHEL 10.2 package availability from dependency '
                    'markdown files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s dependencies-rvps.md --host 10.0.184.129
  %(prog)s dependencies-analysis.md --host 10.0.184.129 --verbose
  %(prog)s dependencies-rvps.md --host 10.0.184.129 --user myuser -v
        """
    )

    parser.add_argument(
        'markdown_file',
        help='Path to dependency markdown file to check'
    )

    parser.add_argument(
        '--host',
        required=True,
        help='RHEL 10.2 host to SSH into (required)'
    )

    parser.add_argument(
        '--user',
        default='root',
        help='SSH user (default: root)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output (show versions)'
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
    checker = RHELPackageChecker(
        host=args.host,
        user=args.user,
        verbose=args.verbose
    )

    print(f"Parsing dependency file: {args.markdown_file}")
    packages = checker.parse_markdown_table(content)

    if not packages:
        print("Warning: No packages found in markdown file")
        print("Make sure the file contains dependency tables with:")
        print("  - A 'Dependency' column")
        print("  - A 'Required Version' column")
        print("  - An 'Available in RHEL 10.2' column")
        return 1

    print(f"Found {len(packages)} packages to verify")

    # Verify packages
    results = checker.verify_packages(packages)

    # Print summary
    success = checker.print_summary(results)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
