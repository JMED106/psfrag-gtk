#!/usr/bin/python
"""
    PyPSfrag - Graphical Tool to replace selected labels in an EPS file into LaTeX format.
    Copyright (C) 2017  Jose M. Esnaola-Acebes

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import yaml
import sys
import logging.config
from colorlog import ColoredFormatter
import os
# import gi
# gi.require_version('Gtk', '3.10')
from gi.repository import Gtk
from gui import MainGui, Data, PSFrag

__author__ = 'Jose M. Esnaola Acebes'

""" Graphical script to replace texts on EPS files using LaTeX engine and psfrag.
"""

print "\n\tPyPSfrag  Copyright (C) 2017  Jose M. Esnaola-Acebes\n"\
      "\tThis program comes with ABSOLUTELY NO WARRANTY; for details see LICENSE.txt.\n"\
      "\tThis is free software, and you are welcome to redistribute it\n"\
      "\tunder certain conditions; see LICENCE.txt for details.\n"

# We first try to parse optional configuration files:
fparser = argparse.ArgumentParser(add_help=False)
fparser.add_argument('-db', '--debug', default="INFO", dest='db', metavar='<debug>',
                     choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
farg = fparser.parse_known_args()
# ####### Debugging #########
debug = getattr(logging, vars(farg[0])['db'].upper(), None)
if not isinstance(debug, int):
    raise ValueError('Invalid log level: %s' % vars(farg[0])['db'])

logformat = "%(log_color)s[%(levelname)-7.8s]%(reset)s %(name)-12.12s:%(funcName)-8.8s: " \
            "%(log_color)s%(message)s%(reset)s"
formatter = ColoredFormatter(logformat, log_colors={
    'DEBUG': 'cyan',
    'INFO': 'white',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white',
})

# Some environmental constants:
scriptpath = os.path.realpath(__file__)
scriptdir = os.path.dirname(scriptpath)

# Logger configuration
logging.config.dictConfig(yaml.load(file('%s/logging.conf' % scriptdir, 'rstored')))
handler = logging.root.handlers[0]
handler.setLevel(debug)
handler.setFormatter(formatter)
logger = logging.getLogger('script')

logger.debug("Scriptpath: %s", scriptpath)
logger.debug("ScriptDir: %s", scriptdir)

# Some other environmental constants:
cwd = os.getcwd()
logger.debug('We are working in %s' % str(cwd))

# PARSER ########################################################################

# We need the name of the eps file, and optionally a file to handle substitutions
logger.debug('Formatting parser')
parser = argparse.ArgumentParser(
    description='Script to convert selected tags in eps files into latex.',
    usage='python %s input.eps [-O <options>]' % sys.argv[0])

parser.add_argument('epsfile', type=str, help='.eps file in which perform the substitutions.')
# The default substitution file will be in the same directory as the script.
parser.add_argument('-s', '--subs', default='%s/subs.tex' % scriptdir, dest='subs', type=str,
                    help='.tex file where the substitutions are located.')
parser.add_argument('-db', '--debug', default="DEBUG", dest='db', metavar='<debug>',
                    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Debbuging level. Default is INFO.')
parser.add_argument('-g', '--nogui', default=False, dest='nogui', action='store_true',
                    help='Run the programm without graphical interface (X11).')
parser.add_argument('-pdf', '--pdf', default=False, dest='pdf', action='store_true',
                    help='Add output format: pdf.')
parser.add_argument('-svg', '--svg', default=False, dest='svg', action='store_true',
                    help='Add output format: svg.')
parser.add_argument('-png', '--png', default=False, dest='png', action='store_true',
                    help='Add output format: png.')
parser.add_argument('--density', default=300, dest='dsty', type=int, help='Density of the png image.')

args = parser.parse_args()
logger.debug('Introduced arguments: %s' % str(args))
args = vars(args)
epspath = args['epsfile']
subspath = args['subs']
logger.debug('.eps file path: %s' % epspath)
logger.debug('.tex file path: %s' % subspath)

# ################################################################################

# Now we create a data structure where the file names, extensions, etc. are treated:
data = Data(epspath, subspath, cwd, args['pdf'], args['svg'], args['png'], args['dsty'])
psfrag = PSFrag(data)

if args['nogui']:
    logger.info("Non-graphical UI selected.")
    if data.tags:
        for tag, rep in zip(data.tags, data.reps):
            if len(data.labels) == 1:
                data.labels[0]['label'] = tag
                data.labels[0]['latex'] = rep
            else:
                data.labels.append({'label': tag, 'latex': rep})
    else:
        logger.error("No substitutions to be made. Exiting.")
        exit(1)

    logger.info("Replacing ...")
    psfrag.create_subs()
    psfrag.do_replace()
    logger.info("Done!")
else:
    mg = MainGui(data, psfrag)
    mg.window.show_all()
    Gtk.main()
