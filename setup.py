import distutils.core

# Uploading to PyPI
# =================
# $ python setup.py register -r pypi
# $ python setup.py sdist upload -r pypi

version = '0.0'
distutils.core.setup(
        name='kxg',
        version=version,
        author='Kale Kundert and Alex Mitchell',
        url='https://github.com/kxgames/GameEngine',
        download_url='https://github.com/kxgames/GameEngine/tarball/'+version,
        license='LICENSE.txt',
        description="A collection of generally useful game libraries.",
        long_description=open('README.rst').read(),
        keywords=['game', 'network', 'gui', 'pyglet'],
        packages=['kxg'],
        requires=[
            'pyglet',
            'nonstdlib',
            'linersock',
            'vecrec',
            'glooey',
            'finalexam',
        ],
)
