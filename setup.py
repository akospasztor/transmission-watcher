#!/usr/bin/env python

from setuptools import setup, find_packages

# Python versions this package is compatible with
python_requires = '>=3.7, <4'

# Packages that this package imports
install_requires = [
]

# Packages required for tests and docs
extras_require = {
    'test': [
        'setuptools',
        'flake8~=7.1.2',
        'pytest~=8.3.5',
        'pytest-cov~=6.0.0',
        'pytest-html~=4.1.1',
    ]
}

# Use README.md and CHANGELOG.md as package description
readme = open('README.md', encoding='utf-8').read()
changelog = open('CHANGELOG.md', encoding='utf-8').read()
long_description = readme.strip() + "\n\n" + changelog.strip() + "\n"

setup(
    name='transmission-watcher',
    version='0.1.0',
    author='Akos Pasztor',
    author_email='mail@akospasztor.com',
    description='',
    keywords='',
    license='proprietary',
    url='https://akospasztor.com',
    packages=find_packages(exclude=['tests', 'tests.*']),
    long_description=long_description,
    python_requires=python_requires,
    install_requires=install_requires,
    extras_require=extras_require,
    classifiers=[
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    entry_points={
        'console_scripts': [
            'transmission-watcher = transmission_watcher.cli:main'],
    },
)
