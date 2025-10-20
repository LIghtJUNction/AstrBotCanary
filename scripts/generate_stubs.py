#!/usr/bin/env python3
"""Generate .pyi stub files for local modules."""

import sys
from pathlib import Path


def find_packages_to_stub(project_root: Path) -> list[dict[str, str]]:
    """Find all packages that need .pyi stub generation."""
    packages: list[dict[str, str]] = []

    # Check astrbot_modules directory - SKIP workspace packages
    # These are local workspace packages, mypy should use source code directly
    # astrbot_modules = project_root / "astrbot_modules"
    # if astrbot_modules.exists():
    #     for module_dir in astrbot_modules.iterdir():
    #         if module_dir.is_dir() and (module_dir / "src").exists():
    #             src_dir = module_dir / "src"
    #             # Find the package name (first directory in src)
    #             for pkg_dir in src_dir.iterdir():
    #                 if pkg_dir.is_dir() and (pkg_dir / "__init__.py").exists():
    #                     packages.append(
    #                         {
    #                             "name": pkg_dir.name,
    #                             "src_dir": str(src_dir),
    #                             "module_dir": str(module_dir),
    #                         },
    #                         break

    # Check src directory for main package - SKIP to avoid conflicts
    # src_dir = project_root / "src"
    # if src_dir.exists():
    #     for pkg_dir in src_dir.iterdir():
    #         if pkg_dir.is_dir() and (pkg_dir / "__init__.py").exists():
    #             packages.append({
    #                 "name": pkg_dir.name,
    #                 "src_dir": str(src_dir),
    #                 "module_dir": ""
    #             })

    # Check astrbot_plugins directory
    astrbot_plugins = project_root / "astrbot_plugins"
    if astrbot_plugins.exists():
        for plugin_dir in astrbot_plugins.iterdir():
            if plugin_dir.is_dir() and (plugin_dir / "__init__.py").exists():
                packages.append(
                    {
                        "name": plugin_dir.name,
                        "src_dir": str(astrbot_plugins),
                        "module_dir": "",
                    },
                )

    return packages


def generate_stubs():
    """Generate .pyi files for all local modules."""
    # Get the project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    packages = find_packages_to_stub(project_root)

    if not packages:
        print("No packages found to generate stubs for.")
        return True

    success = True

    for package in packages:
        print(f"Generating stubs for {package['name']}...")
        try:
            # Import and use mypy.stubgen directly
            from mypy import stubgen

            # Save original argv
            old_argv = sys.argv[:]

            # Set argv for stubgen
            sys.argv = [
                "stubgen",
                "--output",
                package["src_dir"],
                "--package",
                package["name"],
                "--include-private",
            ]

            try:
                # Call stubgen
                stubgen.main()
                print(f"Successfully generated stubs for {package['name']}")
            except SystemExit as e:
                if e.code == 0:
                    print(f"Successfully generated stubs for {package['name']}")
                else:
                    print(
                        f"Error generating stubs for {package['name']}: stubgen exited with code {e.code}",
                    )
                    success = False
            except Exception as e:
                print(f"Error generating stubs for {package['name']}: {e}")
                success = False
            finally:
                # Restore original argv
                sys.argv = old_argv

        except Exception as e:
            print(f"Error generating stubs for {package['name']}: {e}")
            success = False

    if success:
        print("All stub generation completed successfully!")
    else:
        print("Some stub generation failed.")

    return success


if __name__ == "__main__":
    success = generate_stubs()
    sys.exit(0 if success else 1)
