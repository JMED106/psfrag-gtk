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

import os
import re
import sys
import threading

# import gi
# gi.require_version('Gtk', '3.10')
from gi.repository import Gtk, GObject

import logging

logging.getLogger('gui').addHandler(logging.NullHandler())


class Data:
    def __init__(self, filepath="example.eps", subspath="subs.tex", cwd="./",
                 pdf=False, svg=False, png=False, density=300):
        self.logger = logging.getLogger('gui.Data')
        # Paths
        self.epspath = filepath
        self.subspath = subspath
        # Files
        self.subsfile = os.path.basename(subspath)
        self.logger.debug('Subs file: %s' % self.subsfile)
        self.epsfile = os.path.basename(filepath)
        self.logger.debug('Eps file: %s' % self.epsfile)
        # Files names (without extension)
        self.subsname = self.subsfile[0:-4]
        self.logger.debug('Subs file name: %s' % self.subsname)
        self.epsname = self.epsfile[0:-4]
        self.logger.debug('Eps file name: %s' % self.epsname)
        # Dirs
        self.epsdir = os.path.dirname(filepath)
        if self.epsdir == "":
            self.epsdir = "./"
        self.subsdir = os.path.dirname(subspath)
        self.logger.debug('Eps directory: %s' % self.epsdir)
        self.logger.debug('Subs directory: %s' % self.subsdir)

        self.cwd = cwd

        # Output format options
        self.eps = True
        self.pdf = pdf
        self.svg = svg
        self.png = png
        self.density = density  # Default density for png conversion

        # List where the tags and substitutions are stored
        self.labels = [{"label": "", "latex": ""}]

        # Checking files
        self.logger.debug("Checking files ...")
        self.check_file(self.epspath)
        subs = self.check_file(self.subspath, False)

        # Checking extensions
        self.logger.debug("Checking extensions ...")
        for f, ext in zip([self.epsfile, self.subsfile], ['eps', 'tex']):
            self.check_extension(f, ext)

        # Prepare the eps file to read (tags)
        f = open(self.epspath, 'r')
        self.epsimage = f.read()
        # Prepare the subs file to read (tags and replacements)
        self.subspre = None
        self.subsps = None
        if subs:
            f2 = open(self.subspath, 'r')
            self.subs = f2.read()
            self.logger.debug("Loading labels from %s ..." % self.subsfile)
            self.tags, self.reps = self.read_subs()
        else:
            self.subspre = "% BEGIN INFO\n% END INFO\n"
            self.tags = []
            self.reps = []

    def check_file(self, fin, critical=True):
        if not os.path.exists(fin):
            if critical:
                raise IOError('File %s/%s does not exist.' % (self.cwd, fin))
            else:
                self.logger.error('File %s/%s does not exist.' % (self.cwd, fin))
                return False
        else:
            return True

    def check_extension(self, fin, extension):
        if not fin.endswith(extension):
            self.logger.error("File %s is not an %s file." % (fin, extension))
            sys.exit(1)

    def read_subs(self):
        self.subspre = re.findall(r'% BEGIN INFO.*?% END INFO\n', self.subs, re.DOTALL)
        self.subsps = re.findall(r'% BEGIN PS(.*?)% END PS\n', self.subs, re.DOTALL)
        psfrags = re.findall(r'\n.*?%EndPs', self.subsps[0], re.DOTALL)
        tags = []
        reps = []
        plenght = len("\\psfrag{")
        for k, psfrag in enumerate(psfrags):
            if psfrag:
                tag = re.findall(r'\\psfrag{(.*?)}', psfrag)
                length = plenght + len(tag[0])
                tags.append(tag[0])
                rep = re.findall(r']{(.*?)} %EndPs', psfrag[length:])
                if not rep:
                    rep = re.findall(r']{(.*?)}%EndPs', psfrag[length:])[0]
                else:
                    rep = rep[0]
                reps.append(rep)
            else:
                del psfrags[k]
        self.logger.debug(tags)
        self.logger.debug(reps)
        return tags, reps


class PSFrag:
    def __init__(self, data=None):
        self.logger = logging.getLogger('gui.PSFrag')
        if data is None:
            self.d = Data()
        else:
            self.d = data

        # Basic configuration for LaTeX
        self.preamble = "\\documentclass[a4paper]{article}\n" \
                        "\\usepackage{graphicx, psfrag}\n" \
                        "\\begin{document}\n" \
                        "\\pagestyle{empty}\n" \
                        "\\begin{figure}[htbp]\n"

        self.graphic = "\\centerline{\\includegraphics[width=\\textwidth]{%s}}\n" % self.d.epspath
        self.ending = "\\end{figure}\n" \
                      "\\end{document}"

        self.subsname = None

    def check_tag(self, index):
        tag = self.d.labels[index]['label']
        self.logger.debug("Searching for %s ..." % tag)
        # Find the tag in the eps file
        tags = re.findall('\(' + tag + '\) show', self.d.epsimage, re.DOTALL)
        self.logger.debug(tags)
        if len(tags) == 0:
            return False
        else:
            return True

    def create_subs(self):
        filename = "%s/subs-%s.tex" % (self.d.epsdir, self.d.epsname)
        self.subsname = filename
        self.logger.debug("Writing substitution file in %s ..." % filename)
        f = open(filename, 'w')
        f.write(self.d.subspre[0])
        f.write("% BEGIN PS\n")
        for row in self.d.labels:
            f.write("\\psfrag{" + row['label'] + "}[][]{" + row['latex'] + "} %EndPs\n")
        f.write("% END PS\n")
        f.close()
        self.logger.debug("Writing Done!")

    def do_replace(self):
        # Create latex file
        filedir = "%s" % self.d.epsdir
        filename = "%s/%s" % (filedir, self.d.epsname)
        latexname = "%s/%s.tex" % (filedir, self.d.epsname)
        self.logger.debug("Writing latex file in %s ..." % latexname)
        f = open(latexname, 'w')
        f.write(self.preamble)
        f.write("\\input{%s}\n" % self.subsname)
        f.write("\\centerline{\\includegraphics[width=\\textwidth]{%s.eps}}\n" % filename)
        f.write(self.ending)
        f.close()
        self.logger.debug("Writing Done!")

        # Compile latex file
        self.logger.debug("Compiling LaTeX ...")
        os.popen('latex -output-directory=%s -shell-escape -interaction=nonstopmode -file-line-error  %s '
                 '| grep ".*:[0-9]*:.*"' % (filedir, latexname))
        # os.popen('latex %s' % latexname)
        self.logger.debug("Done!")
        self.logger.debug("Transforming dvi -> ps -> pdf -> pdf-crop -> ps-crop -> eps-crop ...")
        os.popen('dvips -o %s.ps -q* %s.dvi' % (filename, filename))
        os.popen('ps2pdf %s.ps %s.pdf' % (filename, filename))
        os.popen('pdfcrop --noverbose %s.pdf | grep nothing' % filename)
        os.popen('pdftops -q %s-crop.pdf' % filename)
        os.popen('ps2eps -q %s-crop.ps' % filename)
        self.logger.debug("Done!")

        self.logger.debug("Removing auxiliary files ...")
        os.popen('rm %s.dvi %s.pdf %s.ps %s-crop.ps' % (filename, filename, filename, filename))
        os.popen('rm %s.aux %s.log' % (filename, filename))
        self.logger.debug("Done!")

        if self.d.svg:
            self.logger.debug("Creating SVG file ...")
            os.popen('pdf2svg %s-crop.pdf %s-latex.svg' % (filename, filename))
            self.logger.debug("Done!")

        if self.d.png:
            self.logger.debug("Creating png file, with density %d ..." % self.d.density)
            os.popen('convert -density %d %s-crop.pdf %s-latex.png' % (self.d.density, filename, filename))
            self.logger.debug("Done!")

        if self.d.pdf:
            self.logger.debug("Creating pdf file ...")
            os.popen('mv %s-crop.pdf %s-latex.pdf' % (filename, filename))
            self.logger.debug("Done!")
        else:
            os.popen('rm %s-crop.pdf' % filename)

        if self.d.eps:
            os.popen('mv %s-crop.eps %s-latex.eps' % (filename, filename))
        else:
            os.popen('rm %s-crop.eps' % filename)

        self.logger.debug("All jobs finished.")


class MainGui:
    def __init__(self, data=None, psfrag=None):
        if data is None:
            self.d = Data()
        else:
            self.d = data

        if psfrag is None:
            self.pf = PSFrag(data)
        else:
            self.pf = psfrag
        self.logger = logging.getLogger('gui.MainGui')
        scriptpath = os.path.realpath(__file__)
        scriptdir = os.path.dirname(scriptpath)

        self.builder = Gtk.Builder()
        self.builder.add_from_file("%s/v0.312.glade" % scriptdir)

        self.window = self.builder.get_object("window1")
        self.window.connect("delete-event", Gtk.main_quit)

        self.densityspin = self.builder.get_object("density")
        self.densityspin.set_value(self.d.density)
        pdfbutton = self.builder.get_object("PDF")
        pdfbutton.set_active(self.d.pdf)
        svgbutton = self.builder.get_object("SVG")
        svgbutton.set_active(self.d.svg)
        pngbutton = self.builder.get_object("png")
        pngbutton.set_active(self.d.png)
        self.listbox = self.builder.get_object("replacements")
        self.im_update = self.builder.get_object("image1")
        self.im_error = self.builder.get_object("image2")
        self.im_ok = self.builder.get_object("image3")
        label = self.builder.get_object("entry2")
        latex = self.builder.get_object("entry3")

        signals = {"on_exit_clicked": self.on_exit_clicked,
                   "gtk_main_quit": Gtk.main_quit,
                   "on_EPS_toggled": self.on_eps_toggled,
                   "on_PDF_toggled": self.on_pdf_toggled,
                   "on_SVG_toggled": self.on_svg_toggled,
                   "on_png_toggled": self.on_png_toggled,
                   "on_density_value_changed": self.on_density_value_changed,
                   "on_label_activate": self.on_label_activate,
                   "on_latex_activate": self.on_latex_activate,
                   "on_add_clicked": self.on_add_clicked,
                   "on_check_clicked": self.on_check_clicked,
                   "on_replace_clicked": self.on_replace_clicked}
        self.builder.connect_signals(signals)
        self.pbar = self.builder.get_object("progressbar1")
        self.repbutton = self.builder.get_object("replace")
        self.timeout_id = None

        # We load the replacements from the subs file, if any:
        if self.d.tags:
            self.logger.debug("Setting default tags and replacements...")
            for tag, rep in zip(self.d.tags, self.d.reps):
                label.set_text(tag)
                self.on_label_activate(label)
                latex.set_text(rep)
                self.on_latex_activate(latex)
                if len(self.d.labels) < len(self.d.tags):
                    label, latex = self.on_add_clicked(None)

    def on_exit_clicked(self, event):
        self.logger.debug('Button %s pressed' % event)
        Gtk.main_quit()

    def on_eps_toggled(self, event):
        self.logger.debug('Button %s pressed' % event)
        self.d.eps = not self.d.eps
        self.logger.debug('EPS: %s' % self.d.eps)

    def on_pdf_toggled(self, event):
        self.logger.debug('Button %s pressed' % event)
        self.d.pdf = not self.d.pdf
        self.logger.debug('PDF: %s' % self.d.pdf)

    def on_svg_toggled(self, event):
        self.logger.debug('Button %s pressed' % event)
        self.d.svg = not self.d.svg
        self.logger.debug('SVG: %s' % self.d.svg)

    def on_png_toggled(self, event):
        self.logger.debug('Button %s pressed' % event)
        self.d.png = not self.d.png
        self.logger.debug('PNG: %s' % self.d.png)

    def on_density_value_changed(self, event):
        self.logger.debug('Value at %s modified' % event)
        self.d.density = self.densityspin.get_value()
        self.logger.debug('Density for PNG conversion: %d' % self.d.density)

    def on_label_activate(self, event):
        self.logger.debug('Text on %s modified' % event)
        box = event.get_parent()
        listboxrow = box.get_parent()

        rowindex = listboxrow.get_index()
        self.listbox.select_row(listboxrow)
        tag = "label"
        self.d.labels[rowindex][tag] = event.get_text()
        self.logger.debug('Text at %s: %s' % (tag, self.d.labels[rowindex][tag]))

    def on_latex_activate(self, event):
        self.logger.debug('Text on %s modified' % event)
        box = event.get_parent()
        listboxrow = box.get_parent()

        rowindex = listboxrow.get_index()
        self.listbox.select_row(listboxrow)
        tag = "latex"
        self.d.labels[rowindex][tag] = event.get_text()
        self.logger.debug('Text at %s: %s' % (tag, self.d.labels[rowindex][tag]))

    def on_add_clicked(self, event):
        self.logger.debug('Button %s pressed' % event)
        newbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.listbox.insert(newbox, -1)
        label_entry = Gtk.Entry()
        label_entry.connect("activate", self.on_label_activate)
        latex_entry = Gtk.Entry()
        latex_entry.connect("activate", self.on_latex_activate)
        button = Gtk.Button(label="Check", image=Gtk.Image(stock="gtk-refresh"))
        button.connect("clicked", self.on_check_clicked)

        newbox.pack_start(label_entry, True, True, padding=4)
        newbox.pack_start(latex_entry, True, True, padding=4)
        newbox.pack_start(button, True, True, padding=4)
        self.d.labels.append({"label": "", "latex": ""})

        self.window.show_all()
        return label_entry, latex_entry

    def on_check_clicked(self, event):
        self.logger.debug('Button %s pressed' % event)
        box = event.get_parent()
        children = box.get_children()
        entry1 = children[0]
        entry2 = children[1]
        self.on_label_activate(entry1)
        self.on_latex_activate(entry2)
        listboxrow = box.get_parent()
        rowindex = listboxrow.get_index()
        self.listbox.select_row(listboxrow)
        # Run a function of rowindex
        exists = self.pf.check_tag(rowindex)
        if exists:
            self.logger.info("Tag %s found." % self.d.labels[rowindex]['label'])
            event.set_image(Gtk.Image(stock="gtk-apply"))
        else:
            self.logger.warning("Tag %s not found." % self.d.labels[rowindex]['label'])
            event.set_image(Gtk.Image(stock="gtk-dialog-error"))

    def on_replace_clicked(self, event):
        self.logger.debug('Button %s pressed' % event)
        self.repbutton.set_image(Gtk.Image(stock='gtk-dialog-warning'))
        self.timeout_id = GObject.timeout_add(50, self.on_timeout, True)
        thread = threading.Thread(target=self.outside_task)
        thread.start()

    def on_timeout(self, user_data):
        self.pbar.pulse()
        return user_data

    def outside_task(self):
        self.pf.create_subs()
        self.pf.do_replace()
        self.logger.info("Replacement done.")
        self.repbutton.set_image(Gtk.Image(stock='gtk-apply'))
        GObject.source_remove(self.timeout_id)
        self.pbar.set_fraction(0.0)
