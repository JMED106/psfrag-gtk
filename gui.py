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
import threading
import urllib
# import gi
# gi.require_version('Gtk', '3.10')
from gi.repository import Gtk, GObject, Gdk

import logging

logging.getLogger('gui').addHandler(logging.NullHandler())
TARGET_TYPE_URI_LIST = 0


class Data:
    def __init__(self, filepath="example.eps", subspath=None, cwd="./",
                 pdf=False, svg=False, png=False, density=300):
        self.logger = logging.getLogger('gui.Data')

        self.cwd = cwd
        self.epscwd = cwd

        if subspath:
            self.subspath = subspath
            # Files (files are stored with absolute paths, if possible)
            self.subsfile = os.path.basename(subspath)
            self.logger.debug('Subs file: %s' % self.subsfile)

            # Files names (without extension)
            self.subsname = self.subsfile[0:-4]
            self.logger.debug('Subs file name: %s' % self.subsname)
            self.ferror = 1

            # Dirs
            self.subsdir = os.path.dirname(subspath)
            self.logger.debug('Subs directory: %s' % self.subsdir)
            # Checking files
            subs = self.check_file(self.subspath, False)
            self.check_extension(self.subsfile, 'tex')
        else:
            subs = False

        # Output format options
        self.eps = True
        self.pdf = pdf
        self.svg = svg
        self.png = png
        self.density = density  # Default density for png conversion

        # List where the tags and substitutions are stored
        # Options are [ posn ][ psposn ][ scale ][ rot ]
        self.default_ops = {"a": 'bl', "b": 'bl', "c": '1.0', "d": '0'}
        self.labels = [{"tag": "", "ltx": "", "opt": dict(self.default_ops)}]

        self.epsimage = ""
        self.epstags = None

        # Paths
        if filepath is None:
            self.epspath = None
            self.epsfile = None
            self.epsname = None
            self.epsdir = None
        else:
            # Opening Eps file
            self.open_epsfile(filepath)

        # Prepare the subs file to read (tags and replacements)
        self.subspre = None
        self.subsps = None
        if subs:
            f2 = open(self.subspath, 'r')
            self.subs = f2.read()
            self.logger.debug("Loading labels from %s ..." % self.subsfile)
            self.tags, self.reps, self.opts = self.read_subs()
        else:
            self.subspre = "% BEGIN INFO\n% END INFO\n"
            self.tags = []
            self.reps = []
            self.opts = []

    def open_epsfile(self, filepath):
        """ Function that sets the variables for opening the input file """

        if filepath[0] == '~':  # We expand (~/)
            self.logger.debug(filepath)
            self.epspath = os.path.expanduser(filepath)
            self.logger.debug(self.epspath)
        else:
            self.epspath = filepath
        self.logger.info("Loading %s ..." % self.epspath)
        self.epsfile = os.path.basename(self.epspath)
        self.logger.debug('Eps file: %s' % self.epsfile)
        self.epsname = self.epsfile[0:-4]
        self.logger.debug('Eps file name: %s' % self.epsname)
        self.epsdir = os.path.dirname(self.epspath)
        self.epscwd = self.epsdir
        if self.epsdir == "":  # If the file has local path format we add ./
            self.epsdir = "./"
        self.logger.debug('Eps directory: %s' % self.epsdir)
        # We check the existance of the file at that path and the extension
        if self.check_file(self.epspath):
            if not self.check_extension(self.epsfile, 'eps'):
                self.epspath = None
                return False
        else:
            self.epspath = None
            return False

        # Prepare the eps file to read (tags)
        f = open(self.epspath, 'r')
        self.epsimage = f.read()
        self.epstags = self.read_tags(self.epsimage)
        return True

    def check_file(self, fin, critical=True):
        """
        Check if the file exists
        :param fin: input file's path.
        :param critical: forces the program to stop if the file is not found. Default is True.
        :return: True if the file exists. False if it does not.
        """
        self.logger.debug("Checking %s file ..." % fin)
        if not os.path.exists(fin):
            if critical:
                raise IOError('File %s/%s does not exist.' % (self.cwd, fin))
            else:
                self.logger.error('File %s/%s does not exist.' % (self.cwd, fin))
                return False
        else:
            return True

    def check_extension(self, fin, extension):
        """
        Check the extension of file fin.
        :param fin: input file's path.
        :param extension: extension to be checked.
        :return: True if the extension coincides.
        """
        self.logger.debug("Checking %s extension ..." % fin)
        if not fin.endswith(extension):
            self.logger.error("File %s is not a %s file." % (fin, extension))
            return False
        else:
            return True

    def read_subs(self):
        """
        Reads the already opened substitutions file. Looks for tags and replacements.
        :return: 'tags' and 'reps' contains tags and replacements found in the psfrag commands.
        """
        # The substitution file should have an specific format:
        # % BEGIN INFO
        # % END INFO
        # % BEGIN PS
        # \psfrag{'tag'}['posn']['psposn']['scale']['rot']{'rep'}
        # % END PS

        self.subspre = re.findall(r'% BEGIN INFO.*?% END INFO\n', self.subs, re.DOTALL)
        self.subsps = re.findall(r'% BEGIN PS(.*?)% END PS\n', self.subs, re.DOTALL)
        tags = []
        reps = []
        opts = []
        ttag, rrep = "", ""
        if self.subsps:
            psfrags = re.findall(r'\\psfrag(.*?)\n', self.subsps[0])
        else:
            self.logger.warning('I did not find any psfrag commands ...')
            return tags, reps

        for k, psfrag in enumerate(psfrags):
            if psfrag:
                tag = re.findall(r'\{(.*?)\}\{|\{(.*?)\}\[', psfrag)
                for t in list(tag[0]):
                    if t != "":
                        ttag = t
                rep = re.findall(r'\]\{(.*?)\}$|\}\{(.*?)\}$', psfrag)
                for t in list(rep[0]):
                    if t != "":
                        rrep = t
                options = psfrag[len(ttag) + 1:-len(rrep) - 1]
                opt = re.findall(r'\[(.*?)\]', options)
                tags.append(ttag)
                reps.append(rrep)
                opts.append(opt)
            else:
                del psfrags[k]

        self.logger.debug(tags)
        self.logger.debug(reps)
        self.logger.debug(opts)
        return tags, reps, opts

    def read_tags(self, epscontent):
        """ Function that reads every tag in the eps-file"""
        creator = re.findall('%%Creator: (.*?)\n', epscontent, re.DOTALL)
        self.logger.debug("Creator of the .eps file: %s" % creator[0])
        if creator[0].startswith('Grace'):
            tags = re.findall('\((.*?)\)', epscontent, re.DOTALL)
            self.logger.debug(tags)
            return tags
        else:
            return None


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
        tag = self.d.labels[index]['tag']
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
        if self.d.subspre:
            f.write(self.d.subspre[0])
        else:
            f.write("% BEGIN INFO\n")
            f.write("% END INFO\n")
            self.logger.warning("Something is not going ok with %s ..." % filename)
            self.logger.warning("There are no tags to replace ...")
        f.write("% BEGIN PS\n")
        for k, row in enumerate(self.d.labels):
            f.write("\\psfrag{" + row['tag'] + "}")
            for key in sorted(row['opt']):
                if key is None:
                    opt = ""
                else:
                    opt = row['opt'][key]
                    if key in ('c', 'd') and opt == '':
                        opt = self.d.default_ops[key]
                f.write("[" + opt + "]")
            f.write("{" + row['ltx'] + "}\n")
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
            self.logger.info("Creating SVG file ...")
            os.popen('pdf2svg %s-crop.pdf %s-latex.svg' % (filename, filename))
            self.logger.info("Done!")

        if self.d.png:
            self.logger.info("Creating png file, with density %d ..." % self.d.density)
            os.popen('convert -density %d %s-crop.pdf %s-latex.png' % (self.d.density, filename, filename))
            self.logger.info("Done!")

        if self.d.pdf:
            self.logger.info("Creating pdf file ...")
            os.popen('mv %s-crop.pdf %s-latex.pdf' % (filename, filename))
            self.logger.info("Done!")
        else:
            os.popen('rm %s-crop.pdf' % filename)

        if self.d.eps:
            os.popen('mv %s-crop.eps %s-latex.eps' % (filename, filename))
            self.logger.info("New EPS file is %s-latex.eps." % filename)
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
        posn = self.builder.get_object("posn")
        psposn = self.builder.get_object("psposn")
        scale = self.builder.get_object("scale")
        rot = self.builder.get_object("rot")
        options = [posn, psposn, scale, rot]
        self.open = self.builder.get_object("file")
        poscombo = self.builder.get_object("comboposn")
        self.pos_store = poscombo.get_model()
        self.active_pos = poscombo.get_active()

        if self.d.epspath is not None:
            self.open.set_text(self.d.epspath)

        signals = {"on_exit_clicked": self.on_exit_clicked,
                   "gtk_main_quit": Gtk.main_quit,
                   "on_EPS_toggled": self.on_eps_toggled,
                   "on_PDF_toggled": self.on_pdf_toggled,
                   "on_SVG_toggled": self.on_svg_toggled,
                   "on_png_toggled": self.on_png_toggled,
                   "on_density_value_changed": self.on_density_value_changed,
                   "on_entry_activate": self.on_entry_activate,
                   "on_combotext_changed": self.on_combo_changed,
                   "on_add_clicked": self.on_add_clicked,
                   "on_check_clicked": self.on_check_clicked,
                   "on_replace_clicked": self.on_replace_clicked,
                   "on_open_clicked": self.on_open_clicked,
                   "on_file_activate": self.on_file_activate,
                   "on_file_drag_data_received": self.on_drag_data}

        dnd_list = [Gtk.TargetEntry.new("text/uri-list", 0, TARGET_TYPE_URI_LIST)]

        self.window.drag_dest_set(Gtk.DestDefaults.MOTION |
                                  Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP,
                                  dnd_list, Gdk.DragAction.COPY)
        self.builder.connect_signals(signals)
        self.pbar = self.builder.get_object("progressbar1")
        self.repbutton = self.builder.get_object("replace")
        self.timeout_id = None

        # We create the listbox for the tags combobox
        if self.d.epstags:
            self.tag_store = self.update_tag_list(self.d.epstags)
        else:
            self.tag_store = Gtk.ListStore(int, str)

        # We load the replacements from the subs file, if any:
        if self.d.tags:
            self.logger.debug("Setting default tags and replacements...")
            for tag, rep, opts in zip(self.d.tags, self.d.reps, self.d.opts):
                label.set_text(tag)
                self.on_entry_activate(label)
                latex.set_text(rep)
                self.on_entry_activate(latex)
                for opt, optentry in zip(opts, options):
                    optentry.set_text(opt)
                    self.on_entry_activate(optentry)
                if len(self.d.labels) < len(self.d.tags):
                    label, latex, options = self.on_add_clicked(None)

    def on_exit_clicked(self, event):
        self.logger.debug('Button %s pressed' % event)
        Gtk.main_quit()

    def on_open_clicked(self, event):
        self.logger.debug('Button %s pressed' % event)
        dialog = Gtk.FileChooserDialog("Please choose a file", self.window, Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_current_folder(self.d.epscwd)
        self.add_filters(dialog)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.logger.debug("Open clicked")
            self.logger.debug("File selected: " + dialog.get_filename())
            if self.d.open_epsfile(dialog.get_filename()):
                self.open.set_text(self.d.epspath)
                self.update_tag_list(self.d.epstags, self.tag_store)
        elif response == Gtk.ResponseType.CANCEL:
            self.logger.debug("Cancel clicked")

        dialog.destroy()

    def on_file_activate(self, event):
        self.logger.debug('Text on %s modified' % event)
        filename = event.get_text()
        self.d.open_epsfile(filename)
        if self.d.epstags:
            self.update_tag_list(self.d.epstags, self.tag_store)

    def on_drag_data(self, event, context, x, y, selection, target_type, timestamp):
        self.logger.debug('Something dropped on %s' % event)
        self.logger.debug('Target type: %s' % target_type)
        if target_type == TARGET_TYPE_URI_LIST:
            self.logger.debug(selection.get_data())
            uri = selection.get_data().strip('\r\n\x00')
            uri_splitted = uri.split()  # we may have more than one file dropped
            for uri in uri_splitted:
                path = self.get_file_path_from_dnd_dropped_uri(uri)
                if os.path.isfile(path):  # is it file?
                    self.logger.debug("Dropped file name: %s" % path)
                    self.d.open_epsfile(path)
                    if self.d.epstags:
                        self.update_tag_list(self.d.epstags, self.tag_store)

    @staticmethod
    def get_file_path_from_dnd_dropped_uri(uri):
        # get the path to file
        path = ""
        if uri.startswith('file:\\\\\\'):  # windows
            path = uri[8:]  # 8 is len('file:///')
        elif uri.startswith('file://'):  # nautilus, rox
            path = uri[7:]  # 7 is len('file://')
        elif uri.startswith('file:'):  # xffm
            path = uri[5:]  # 5 is len('file:')

        path = urllib.url2pathname(path)  # escape special chars
        path = path.strip('\r\n\x00')  # remove \r\n and NULL
        return path

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

    def on_entry_activate(self, entry):
        self.logger.debug('Text on %s modified' % entry)
        name = entry.get_name()
        self.logger.debug('Entry widget name: %s' % name)

        parent = entry.get_parent()
        self.logger.debug('Parent of %s: %s' % (name, parent.get_name()))
        if parent.get_name() in ('GtkComboBox', 'GtkComboBoxText'):
            listboxrow = parent.get_parent().get_parent()
        elif parent.get_name() == 'GtkBox':
            listboxrow = parent.get_parent()
        else:
            self.logger.error('Widget not registered')
            return 1

        rowindex = listboxrow.get_index()
        self.listbox.select_row(listboxrow)
        tag = name[0:3]
        if tag == 'opt':
            op = name[3]
            self.d.labels[rowindex][tag][op] = entry.get_text()
        else:
            self.d.labels[rowindex][tag] = entry.get_text()
        self.logger.debug('Text at %s: %s' % (name, self.d.labels[rowindex][tag]))

    def on_combo_changed(self, widget):
        self.logger.debug('ComboBox %s changed' % widget)
        entry = widget.get_child()
        self.logger.debug("Entered: %s" % entry.get_text())
        self.on_entry_activate(entry)

    def on_add_clicked(self, event):
        """ Add a new row to the list box, identical to the previous ones """
        self.logger.debug('Button %s pressed' % event)
        newbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)  # The box containing the widgets
        row = self.listbox.insert(newbox, -1)                     # The new listboxrow
        row_index = len(self.d.labels) + 1

        # First child
        label_combobox = Gtk.ComboBoxText.new_with_entry()        # The tag combobox with entry
        label_entry = label_combobox.get_children()[0]
        label_entry.connect("activate", self.on_entry_activate)
        label_entry.set_name("tag%d" % row_index)
        newbox.pack_start(label_combobox, True, True, padding=4)

        # Second child
        posn = Gtk.ComboBox.new_with_model_and_entry(self.pos_store)
        posn.set_entry_text_column(0)
        posn.set_active(self.active_pos)
        posn.connect("changed", self.on_combo_changed)
        posn_entry = posn.get_children()[0]
        # Properties of the entry
        posn_entry.set_width_chars(2)
        posn_entry.set_max_width_chars(2)
        posn_entry.set_max_length(2)
        posn_entry.connect("activate", self.on_entry_activate)
        posn_entry.set_name("opta%d" % row_index)
        newbox.pack_start(posn, True, False, padding=2)

        # Third child
        psposn = Gtk.ComboBox.new_with_model_and_entry(self.pos_store)
        psposn.set_entry_text_column(0)
        psposn.set_active(self.active_pos)
        psposn.connect("changed", self.on_combo_changed)
        psposn_entry = psposn.get_children()[0]
        # Properties of the entry
        psposn_entry.set_width_chars(2)
        psposn_entry.set_max_width_chars(2)
        psposn_entry.set_max_length(2)
        psposn_entry.connect("activate", self.on_entry_activate)
        psposn_entry.set_name("optb%d" % row_index)
        # psposn_entry.connect("activate", self.on_psposn_activate)
        newbox.pack_start(psposn, True, False, padding=2)

        # Fourth child
        scale = Gtk.Entry(width_chars=3, max_width_chars=3, max_length=3)
        scale.set_alignment(0.5)
        scale.connect("activate", self.on_entry_activate)
        scale.set_name("optc%d" % row_index)
        newbox.pack_start(scale, True, False, padding=4)

        # Fifht child
        adjustment = Gtk.Adjustment(0, 0, 360, 10, 60, 0)
        rot = Gtk.SpinButton(adjustment=adjustment, numeric=True, width_chars=3, max_width_chars=3, max_length=3)
        rot.set_alignment(1.0)
        rot.connect("activate", self.on_entry_activate)
        rot.connect("value-changed", self.on_entry_activate)
        rot.set_name("optd%d" % row_index)
        newbox.pack_start(rot, True, False, padding=4)

        # Sixth child
        latex_entry = Gtk.Entry()
        latex_entry.connect("activate", self.on_entry_activate)
        latex_entry.set_name("ltx%d" % row_index)
        newbox.pack_start(latex_entry, True, False, padding=4)

        # Last child
        button = Gtk.Button(label="Check", image=Gtk.Image(stock="gtk-find"))
        button.connect("clicked", self.on_check_clicked)
        newbox.pack_start(button, True, False, padding=4)

        if self.d.epstags:
            self.update_combobox(self.tag_store, row=row)

        self.d.labels.append({"tag": "", "ltx": "", "opt": dict(self.d.default_ops)})

        self.window.show_all()
        options = [posn_entry, psposn_entry, scale, rot]
        return label_entry, latex_entry, options

    def on_check_clicked(self, event):
        """ Check whether the introduced tag exists """
        self.logger.debug('Button %s pressed' % event)
        box = event.get_parent()  # We obtain the box (parent of the button)
        children = box.get_children()  # We obtain the children in the listbox
        combobox1 = children[0]  # The tag combobox is the first child
        entry1 = combobox1.get_children()[0]  # We select the entry in the tag combobox
        entry2 = children[-2]  # The latex entry is the second last child
        self.on_entry_activate(entry1)  # We make sure the data in the entries is stored in memory
        self.on_entry_activate(entry2)
        listboxrow = box.get_parent()  # Get the row in the listbox
        rowindex = listboxrow.get_index()  # Get the row index
        self.listbox.select_row(listboxrow)  # Select the row, and highlight
        # Run a function of rowindex           # Look for the tag in the input file
        if self.d.epspath:
            exists = self.pf.check_tag(rowindex)
            if exists:
                self.logger.info("Tag %s found." % self.d.labels[rowindex]['tag'])
                event.set_image(Gtk.Image(stock="gtk-apply"))
            else:
                self.logger.warning("Tag %s not found." % self.d.labels[rowindex]['tag'])
                event.set_image(Gtk.Image(stock="gtk-dialog-warning"))
        else:
            exists = False
            self.logger.warning("There is no EPS file loaded.")
            event.set_image(Gtk.Image(stock="gtk-dialog-error"))
            dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.CANCEL,
                                       "Load an EPS file first.")
            dialog.run()
            dialog.destroy()

    def on_replace_clicked(self, event):
        self.logger.debug('Button %s pressed' % event)
        if self.d.epspath:
            self.repbutton.set_image(Gtk.Image(stock='gtk-dialog-warning'))
            self.timeout_id = GObject.timeout_add(50, self.on_timeout, True)
            thread = threading.Thread(target=self.outside_task)
            thread.start()
        else:
            self.logger.warning("There is no EPS file loaded.")
            dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.CANCEL,
                                       "Load an EPS file first.")
            dialog.run()
            dialog.destroy()

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

    def update_tag_list(self, tags, listtags=None):
        if listtags is not None:
            del listtags

        tag_store = Gtk.ListStore(int, str)
        # tag_store.append([0, ""])
        if tags:
            for k, tag in enumerate(tags):
                tag_store.append([k, tag])
        self.update_combobox(tag_store)
        return tag_store

    def update_combobox(self, taglist, row=None):
        if row is None:
            listbox = self.listbox.get_children()
        else:
            listbox = [row]
        for listboxrow in listbox:
            box = listboxrow.get_children()[0]
            combobox = box.get_children()[0]
            combobox.set_model(taglist)
            combobox.set_entry_text_column(1)

    @staticmethod
    def add_filters(dialog):
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Eps Files")
        filter_text.add_mime_type("application/postscript")
        dialog.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)
