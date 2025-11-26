from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="exostream",
    version="0.2.0",
    author="Naman",
    description="Stream webcam from Raspberry Pi using NDI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.8",
    install_requires=[
        # Note: FFmpeg with NDI support must be installed separately
        # See README for installation instructions
        "rich>=13.0.0",
        "click>=8.0.0",
        "pyyaml>=6.0",
        "psutil>=5.9.0",
    ],
    entry_points={
        "console_scripts": [
            "exostream=exostream.cli:main",
        ],
    },
    include_package_data=True,
)

