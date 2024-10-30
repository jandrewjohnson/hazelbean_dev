import math, os, sys, time, random, shutil, logging, csv, json


import scipy
import numpy as np
from osgeo import gdal, osr, ogr
import pandas as pd
import geopandas as gpd
from collections import OrderedDict
import logging

import hazelbean as hb

from hazelbean.ui import validation
import os, sys, math, random, shutil, logging
from collections import OrderedDict

from hazelbean.ui import model, inputs
L = hb.get_logger('seals', logging_level='debug')
dev_mode = True




class AutoUI(model.InVESTModel):
    def __init__(self, project):
        self.p = project

        model.InVESTModel.__init__(self,
                                   # label=u'seals',
                                   label=u'User Interface',
                                   target=self.p.execute,
                                   validator=self.p.validate,
                                   localdoc='../documentation')

        if not getattr(self.p, 'args', None):
            self.p.args = OrderedDict()

        # Analyze args for ui elements to add
        for k, v in self.p.args.items():
            last_in_key = k.split('_')[-1]
            before_last_in_key = k.split('_')[0:-1]
            key_as_title = k.replace('_', ' ').title()
            if last_in_key == 'path':
                ui_element = inputs.File(
                    args_key=k,
                    helptext=(''),
                    label=key_as_title,
                    validator=None)
            elif last_in_key == 'dir':
                ui_element = inputs.Folder(
                    args_key=k,
                    helptext=(''),
                    label=key_as_title,
                    validator=None)
            elif last_in_key == 'checkbox':
                ui_element = inputs.Checkbox(key_as_title, helptext='help', args_key=k)
                # ui_element.checkbox.setChecked(False)
            else:
                ui_element = None

            setattr(self, k, ui_element)
            self.add_input(ui_element)

        # NOTE, containers dont need a seperate interactivity slot. has it  by default it seems
        self.advanced_options_container = inputs.Container(
            args_key='advanced_options_container',
            expandable=True,
            expanded=False,
            interactive=True,
            label='Show advanced options')
        self.add_input(self.advanced_options_container)


        self.run_dir = inputs.Folder('run_dir', helptext='help', args_key='run_dir')
        self.advanced_options_container.add_input(self.run_dir)

        self.basis_dir = inputs.Folder('basis_dir', helptext='help', args_key='basis_dir')
        self.advanced_options_container.add_input(self.basis_dir)


        # Process runtime conditionals
        for name, task in self.p.functions.items():
            if name not in self.p.tasks_to_exclude:
                ui_element = inputs.Checkbox(name, helptext='help', args_key=name + '_cb')
                self.advanced_options_container.add_input(ui_element)

    def assemble_args(self):
        self.p.args[self.workspace.args_key] = self.workspace.value()
        self.p.args[self.suffix.args_key] = self.suffix.value()
        # L.debug('Assembling args called by AutoUI object')
        for k, v in self.p.args.items():
            # L.debug('In self.p.args, found k, v of: ' + str(k) + ', ' + str(v))
            ga = getattr(self, k, None)

            if ga:
                if type(ga) in [inputs.File, inputs.Folder]:
                    self.p.args[k] = getattr(self, k).textfield.text()
                if type(ga) in [inputs.Checkbox]:
                    self.p.args[k] = getattr(self, k).checkbox.isChecked()
        # TODOO Could pull this into a separately define HazelbeanUI class and have it automatically add it as hidden options.
        # Two special values are the run_dir and the basis_dir. By default, all intermediate files are saved to the intermediate_dir, but if run_dir is specified, newly-created files will be saved there. If a file is not created on a particular run, the UI will look for it in the intermedaite dir, unless a different basis_dir is specified.
        if self.run_dir.value() == 'temp':
            self.p.args[self.run_dir.args_key] = hb.make_run_dir(hb.TEMPORARY_DIR, 'seals', just_return_string=True)
            self.run_dir.textfield.setText(self.p.args[self.run_dir.args_key])
        elif not self.run_dir.value():
            self.p.args[self.run_dir.args_key] = os.path.join(self.p.args[self.workspace.args_key], 'intermediate')
        else:
            self.p.args[self.run_dir.args_key] = self.run_dir.value()

        if not self.basis_dir.value():
            self.p.args[self.basis_dir.args_key] = os.path.join(self.p.args[self.workspace.args_key], 'intermediate')
        else:
            self.p.args[self.basis_dir.args_key] = self.basis_dir.value()


        return self.p.args

    def update_project_attribtues_with_args(self, args_odict):
        for k, v in args_odict.items():
            #LEARNING POINT, only the setattr method worked because k wasnt yet set
            # p.k = v
            setattr(p, k, v)


