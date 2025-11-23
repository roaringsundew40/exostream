"""Main CLI entry point for ExoStream"""

import click
from exostream.sender.cli import send


@click.group()
@click.version_option(version="0.1.0")
def main():
    """ExoStream - Stream webcam from Raspberry Pi using GStreamer and SRT"""
    pass


# Add subcommands
main.add_command(send)


if __name__ == '__main__':
    main()

