# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import shlex
import shutil
import subprocess
import sys
ROOT_PATH = os.path.abspath(os.path.join(os.path.pardir, os.path.pardir))
sys.path.insert(0, ROOT_PATH)
from setup import _get_git_version  # pylint: disable=C0413

# -- Project information -----------------------------------------------------

project = 'RunPerf'
copyright = '2023, Lukáš Doktor'
author = 'Lukáš Doktor'

# The full version, including alpha/beta/rc tags
release = _get_git_version()
if release == '0.0':
    # Probably in shallow-cloned git, fetch the latest tag
    try:
        subprocess.call([shutil.which("git"), "fetch",  # nosec
                         "--depth=500"])
        release = _get_git_version()
    except subprocess.SubprocessError:
        pass

# -- API docs ----------------------------------------------------------------
API_SOURCE_DIR = os.path.join(ROOT_PATH, 'bisecter')
BASE_API_OUTPUT_DIR = os.path.join(ROOT_PATH, 'docs', 'source', 'api')
APIDOC = shutil.which('sphinx-apidoc')
APIDOC_TEMPLATE = APIDOC + " -o %(output_dir)s %(API_SOURCE_DIR)s %(exclude_dirs)s"

# Documentation sections. Key is the name of the section, followed by:
# Second level module name (after bisecter), Module description,
# Output directory, List of directory to exclude from API  generation,
# list of (duplicated) generated reST files to remove (and avoid warnings)
API_SECTIONS = {"Runperf API": (None,
                                "API documentation",
                                "bisecter",
                                tuple(),
                                ('modules.rst',)), }

subprocess.call([shutil.which("find"), BASE_API_OUTPUT_DIR, "-name",  # nosec
                 "*.rst", "-delete"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for (section, params) in API_SECTIONS.items():
    output_dir = os.path.join(BASE_API_OUTPUT_DIR, params[2])
    exclude_dirs = [os.path.join(API_SOURCE_DIR, d)
                    for d in params[3]]
    exclude_dirs = " ".join(exclude_dirs)
    files_to_remove = [os.path.join(BASE_API_OUTPUT_DIR, output_dir, d)
                       for d in params[4]]

    # generate all rst files
    cmd = shlex.split(APIDOC_TEMPLATE % locals())
    subprocess.call([shutil.which(cmd[0])] + cmd[1:],  # nosec
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # remove unnecessary ones
    for f in files_to_remove:
        try:
            os.unlink(f)
        except OSError:
            pass
    '''
    # rewrite first lines of main rst file for this section
    second_level_module_name = params[0]
    if second_level_module_name is None:
        main_rst = os.path.join(output_dir,
                                "bisecter.rst")
    else:
        main_rst = os.path.join(output_dir,
                                "bisecter.%s.rst" % second_level_module_name)
    if not APIDOC:
        main_rst_content = []
        try:
            os.makedirs(os.path.dirname(main_rst))
        except OSError as details:
            pass
    else:
        with open(main_rst) as main_rst_file:
            main_rst_content = main_rst_file.readlines()

    new_main_rst_content = [section, "=" * len(section), "",
                            params[1], ""]
    with open(main_rst, "w") as new_main_rst:
        new_main_rst.write("\n".join(new_main_rst_content))
        new_main_rst.write("".join(main_rst_content[2:]))
    '''

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.intersphinx',
              'sphinx.ext.todo']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'classic'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

html_theme_options = {'body_max_width': '90%'}

intersphinx_mapping = {'python': ('http://docs.python.org/3', None)}  # pylint: disable=C0103

autoclass_content = 'both'  # pylint: disable=C0103


# A list of (type, target) tuples (by default empty) that should be ignored
# when generating warnings in “nitpicky mode”.
nitpick_ignore = [
    ('py:class', 'aexpect.client.ShellSession'),
]
