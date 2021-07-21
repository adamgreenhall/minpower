# pip install sphinx, sphinxcontrib-programoutput
import sys, os

# if you don't have minpower in your python path
# sys.path.insert(0, os.path.abspath('../../minpower')) #code location

# General information about the project.
project = "minpower"
copyright = "Adam Greenhall"
author = "Adam Greenhall"
html_theme = "alabaster"

# -- General configuration -----------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    # 'matplotlib.sphinxext.mathmpl',
    # "matplotlib.sphinxext.only_directives",
    "matplotlib.sphinxext.plot_directive",
    # "sphinxcontrib.programoutput",
    #'ipython_console_highlighting',
    #'inheritance_diagram',
    #'numpydoc'
]
pygments_style = "sphinx"
intersphinx_mapping = {"python": ("https://docs.python.org/3.9/", None)}
# extensions.append('mathjax')
mathjax_path = (
    "http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"
)

source_suffix = ".rst"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build"]
templates_path = ["_templates"]
html_static_path = ["_static"]
html_sidebars = {"**": ["globaltoc.html", "searchbox.html"]}

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False
