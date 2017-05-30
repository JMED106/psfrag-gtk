PyPSfrag - PSfrag, python utility
=================================

PyPSfrag is a graphical tool to replace labels (tags) in EPS files into LaTeX format using PSfrag package.
Easy to use, modify and extend.

It is build into `Python <http://www.python.org/>`_, and the GUI is based on `GTK+ 3 <https://developer.gnome.org/gtk3/stable/>`_.
You can find a quick tutorial into `Python GTK+ 3 <https://python-gtk-3-tutorial.readthedocs.io/en/latest/index.html>`_.

The program reads the input .eps file, looks for selected (introduced by user) tags, and replace them with LaTeX formatted content
using psfrag package. Allowed output formats include EPS, PDF, SVG and PNG.


INSTALLATION
------------

Download the project and uncompress it into any directory:

https://github.com/JMED106/pypsfrag/archive/v0.2.zip


It does not require installation but some python dependencies need to be fulfilled:

- gi, Gtk >= 3.10
- logging
- colorlog
- argparse
- yaml

In general, in a Debian based system is enough to run: ::
# apt-get install python-yaml python-colorlog

You can make an alias at ~/.bashrc:

alias pypsfrag='/path/to/pypsfrag.py'

to be able to execute the program in a terminal.

HOW TO USE PyPSfrag
-------------------

PyFrag is a python script that runs in a terminal, and offers a GUI in runtime.
You need to provide the target .EPS file to the program: ::

$ /path/to/pypsfrag.py [-f epsfile.eps] [-O options]

where /path/to/ is the directory where pypsfrag.py is located. ::

$ pypsfrag [-f epsfile.eps] [-O options]

if you have an alias established.

You can also run the program (in graphical inteface, X11), typing: ::

$ pypsfrag

from there you will be able to open the input .eps file.


The program will load a default substitution file (with the script), where psfrag commands are stored.
If the file is not found it will not load any substitution.

You can provide optional substitution files with the option [-s subs-file.tex]. ::

$ pypsfrag [-f epsfile.eps] -s subs-file.tex [-O options]

Example
******* 
To open example.eps file (provided with the package, located in ./example/): ::

$ pypsfrag -f example/example.eps

To avoid loading any default substitutions, use -s None (in graphical interface): ::

$ pypsfrag -f example/example.eps -s None





