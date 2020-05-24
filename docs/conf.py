#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

project = 'KXG Game Engine'
copyright = '2015, Kale Kundert and Alex Mitchell'
version = '0.0'
release = '0.0'

master_doc = 'index'
source_suffix = '.rst'
templates_path = ['templates']
html_static_path = ['static']
exclude_patterns = ['build']
default_role = 'any'


extensions = [
        'ext.show_nodes',
        'autoclasstoc',
        'sphinx.ext.autodoc',
        'sphinx.ext.autosummary',
        'sphinx.ext.intersphinx',
        'sphinx.ext.coverage',
        'sphinx.ext.viewcode',
]

autodoc_default_options = {
        'exclude-members': '__weakref__,__dict__,__module__',
        #'members': True,
        #'undoc-members': True,
        #'special-members': True,
        #'private-members': True,
}
intersphinx_mapping = {
        'http://docs.python.org/': None,
}
autosummary_generate = True
pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'
