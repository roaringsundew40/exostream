"""Main CLI entry point for Exostream"""

# Import the new CLI implementation
from exostream.cli.main import cli

# Export cli as main for setuptools entry point
main = cli


if __name__ == '__main__':
    cli(obj={})

