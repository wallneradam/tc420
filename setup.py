import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()
# We have list of requirements in the requirements.txt
REQUIREMENTS = (HERE / "requirements.txt").read_text().splitlines()

# This call to setup() does all the work
setup(
    name="tc420",
    version="0.1.1",
    description="TC420 LED Controller library and command line interface",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/wallneradam/tc420",
    author="Adam Wallner",
    author_email="adam.wallner@gmail.com",
    license="GPLv3+",
    packages=["tc420"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware :: Hardware Drivers",
        "Topic :: Home Automation",
    ],
    install_requires=REQUIREMENTS,
    entry_points={
        "console_scripts": [
            "tc420=tc420.__main__:main",
        ]
    },
)
