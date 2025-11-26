"""Main CLI entry point for Exostream"""

import click
from exostream.sender.cli import send


@click.group()
@click.version_option(version="0.2.0")
def main():
    """Exostream - Stream webcam from Raspberry Pi using NDI"""
    pass


# Add subcommands
main.add_command(send)


if __name__ == '__main__':
    main()

