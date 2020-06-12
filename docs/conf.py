#!/usr/bin/env python3

import sys, os
from autoclasstoc import Section, PublicMethods, is_method
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
        'autoclasstoc',
        'sphinx.ext.autodoc',
        'sphinx.ext.autosummary',
        'sphinx.ext.coverage',
        'sphinx.ext.inheritance_diagram',
        'sphinx.ext.intersphinx',
        'sphinx.ext.viewcode',
]

autodoc_default_options = {
        'exclude-members': '__weakref__,__dict__,__module__',
}
intersphinx_mapping = {
        'http://docs.python.org/': None,
        'https://pyglet.readthedocs.io/en/latest/': None,
}
autosummary_generate = True
pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'

class EventHandler(Section):
    key = 'event-handlers'
    title = "Event Handlers:"

    def predicate(self, name, attr, meta):
        return is_event_handler(name, attr)

class PublicMethods(PublicMethods):

    def predicate(self, name, attr, meta):
        return super().predicate(name, attr, meta) and not is_event_handler(name, attr)

def is_event_handler(name, attr):
    return is_method(name, attr) and name.startswith('on_')

autoclasstoc_sections = [
        'event-handlers',
        'public-methods',
        'private-methods',
]
