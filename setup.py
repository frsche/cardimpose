from setuptools import setup, find_packages

setup(
    name='cardimpose',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'pymupdf',
        # Add other dependencies here
    ],
    entry_points={
        'console_scripts': [
            'cardimpose = cardimpose.cardimpose:main',
        ],
    },
)
