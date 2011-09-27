import sys, os

sys.path.insert(0, os.path.abspath('../minpower')) #code location
#sys.path.append(os.path.abspath('_build/sphinxext'))
#sys.path.append(os.path.abspath('sphinxext'))

# General information about the project.
project = 'minpower'
copyright = 'Adam Greenhall'
version = '0.1'
release = '0.1 alpha'

# -- General configuration -----------------------------------------------------
extensions = [
          'sphinx.ext.autodoc',
          'sphinx.ext.doctest',
          'sphinx.ext.intersphinx',
          'sphinx.ext.viewcode',

          'matplotlib.sphinxext.mathmpl',
          'matplotlib.sphinxext.only_directives',
          'matplotlib.sphinxext.plot_directive',


          #'ipython_console_highlighting',
          #'inheritance_diagram',
          #'numpydoc'
          ]
extensions.append('mathjax')
mathjax_path = 'http://mathjax.connectmv.com/MathJax.js'

intersphinx_mapping = {'python': ('http://docs.python.org/release/2.7.1/', None)}

templates_path = ['_templates']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

pygments_style = 'sphinx'

# -- Options for HTML output ---------------------------------------------------
html_theme = 'default'
html_title = 'minpower' #postpend to page titles

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars ={'**':['globaltoc.html','searchbox.html']}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = 'http://adamgreenhall.com/minpower'

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'minpower'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'minpower.tex', u'minpower documentation',
   u'Adam Greenhall', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'minpower', u'minpower documentation',
     [u'Adam Greenhall'], 1)
]
