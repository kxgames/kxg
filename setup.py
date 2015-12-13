#!/usr/bin/env python3
# encoding: utf-8

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import re
with open('kxg/__init__.py') as file:
    version_pattern = re.compile("__version__ = '(.*)'")
    version = version_pattern.search(file.read()).group(1)

with open('README.rst') as file:
    readme = file.read()

setup(
    name='kxg',
    version=version,
    author='Kale Kundert and Alex Mitchell',
    author_email='kale@thekunderts.net',
    description='A multiplayer game engine.',
    long_description=readme,
    url='https://github.com/kxgames/kxg',
    packages=[
        'kxg',
    ],
    include_package_data=True,
    install_requires=[
            'pyglet',
            'nonstdlib',
            'linersock',
            'docopt',
    ],
    license='MIT',
    zip_safe=False,
    keywords=[
        'kxg',
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries',
    ],
)
