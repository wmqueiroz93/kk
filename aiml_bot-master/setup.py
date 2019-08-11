"""
AIML Bot implements an interpreter for AIML, the Artificial Intelligence
Markup Language developed by Dr. Richard Wallace of the A.L.I.C.E. Foundation.
It can be used to implement a conversational AI program.
"""

from setuptools import setup
import glob
import os
import warnings

package_prefix = "Lib/site-packages/aiml_bot"


def get_long_description():
    """Load the long description from the README file. In the process,
    convert the README from .md to .rst using Pandoc, if possible."""
    rst_path = os.path.join(os.path.dirname(__file__), 'README.rst')
    md_path = os.path.join(os.path.dirname(__file__), 'README.md')

    try:
        # Imported here to avoid creating a dependency in the setup.py
        # if the .rst file already exists.

        # noinspection PyUnresolvedReferences,PyPackageRequirements
        from pypandoc import convert_file
    except ImportError:
        warnings.warn("Module pypandoc not installed. Unable to generate README.rst.")
    else:
        # First, try to use convert_file, assuming Pandoc is already installed.
        # If that fails, try to download & install it, and then try to convert
        # again.
        # noinspection PyBroadException
        try:
            # pandoc, you rock...
            rst_content = convert_file(md_path, 'rst')
            with open(rst_path, 'w') as rst_file:
                for line in rst_content.splitlines(keepends=False):
                    rst_file.write(line + '\n')
        except Exception:
            try:
                # noinspection PyUnresolvedReferences,PyPackageRequirements
                from pypandoc.pandoc_download import download_pandoc

                download_pandoc()
            except FileNotFoundError:
                warnings.warn("Unable to download & install pandoc. Unable to generate README.rst.")
            else:
                # pandoc, you rock...
                rst_content = convert_file(md_path, 'rst')
                with open(rst_path, 'w') as rst_file:
                    for line in rst_content.splitlines(keepends=False):
                        rst_file.write(line + '\n')

    if os.path.isfile(rst_path):
        with open(rst_path) as rst_file:
            return rst_file.read()
    else:
        # It will be messy, but it's better than nothing...
        with open(md_path) as md_file:
            return md_file.read()


setup(
    name="AIML Bot",
    version="0.0.3",
    author="Cort Stratton",
    author_email="cort@cortstratton.org",
    license="BSD-2-Clause",
    maintainer="Aaron Hosford",
    maintainer_email="hosford42@gmail.com",
    description="An interpreter package for AIML, the Artificial Intelligence Markup Language",
    long_description=get_long_description(),
    url="https://github.com/hosford42/aiml_bot",

    platforms=["any"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Communications :: Chat",
        "Topic :: Scientific/Engineering :: Artificial Intelligence"
    ],

    packages=["aiml_bot"],
    package_data={
        "aiml_bot": ["*.aiml"],
    },
    data_files=[
        ("doc/aiml_bot", glob.glob("*.txt")),
        ("doc/aiml_bot", glob.glob("*.md")),
    ]
)
