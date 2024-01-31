from setuptools import setup, find_packages
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='cardimpose',
    version='0.2.0',
    description='Impose multiple copies of a pdf onto a larger document.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Frederik Scheerer',
    url='https://github.com/frsche/cardimpose',

    packages=find_packages(),
    install_requires=[
        'pymupdf',
    ],
    entry_points={
        'console_scripts': [
            'cardimpose = cardimpose.__main__:main',
        ],
    },
    keywords='imposition, print, pdf'
)
