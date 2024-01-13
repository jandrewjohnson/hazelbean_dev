# coding=UTF-8
import functools

from natcap.invest.ui import model, inputs
from natcap.invest.habitat_risk_assessment import hra, hra_preprocessor


class HabitatRiskAssessment(model.InVESTModel):
    def __init__(self):
        model.InVESTModel.__init__(
            self,
            label='Habitat Risk Assessment',
            target=hra.execute,
            validator=hra.validate,
            localdoc='../documentation/habitat_risk_assessment.html')

        self.csv_uri = inputs.Folder(
            args_key='csv_uri',
            helptext=(
                "A folder containing multiple CSV files.  Each file "
                "refers to the overlap between a habitat and a "
                "stressor pulled from habitat and stressor shapefiles "
                "during the run of the HRA Preprocessor."),
            label='Criteria Scores CSV Folder',
            validator=self.validator)
        self.add_input(self.csv_uri)
        self.grid_size = inputs.Text(
            args_key='grid_size',
            helptext=(
                "The size that should be used to grid the given "
                "habitat and stressor shapefiles into rasters.  This "
                "value will be the pixel size of the completed raster "
                "files."),
            label='Resolution of Analysis (meters)',
            validator=self.validator)
        self.add_input(self.grid_size)
        self.risk_eq = inputs.Dropdown(
            args_key='risk_eq',
            helptext=(
                "Each of these represents an option of a risk "
                "calculation equation.  This will determine the "
                "numeric output of risk for every habitat and stressor "
                "overlap area."),
            label='Risk Equation',
            options=['Multiplicative', 'Euclidean'])
        self.add_input(self.risk_eq)
        self.decay_eq = inputs.Dropdown(
            args_key='decay_eq',
            helptext=(
                "Each of these represents an option for decay "
                "equations for the buffered stressors.  If stressor "
                "buffering is desired, these equtions will determine "
                "the rate at which stressor data is reduced."),
            label='Decay Equation',
            options=['None', 'Linear', 'Exponential'])
        self.add_input(self.decay_eq)
        self.max_rating = inputs.Text(
            args_key='max_rating',
            helptext=(
                "This is the highest score that is used to rate a "
                "criteria within this model run.  These values would "
                "be placed within the Rating column of the habitat, "
                "species, and stressor CSVs."),
            label='Maximum Criteria Score',
            validator=self.validator)
        self.add_input(self.max_rating)
        self.max_stress = inputs.Text(
            args_key='max_stress',
            helptext=(
                "This is the largest number of stressors that are "
                "suspected to overlap.  This will be used in order to "
                "make determinations of low, medium, and high risk for "
                "any given habitat."),
            label='Maximum Overlapping Stressors',
            validator=self.validator)
        self.add_input(self.max_stress)
        self.aoi_tables = inputs.File(
            args_key='aoi_tables',
            helptext=(
                "An OGR-supported vector file containing feature "
                "subregions.  The program will create additional "
                "summary outputs across each subregion."),
            label='Subregions (Vector)',
            validator=self.validator)
        self.add_input(self.aoi_tables)

    def assemble_args(self):
        args = {
            self.workspace.args_key: self.workspace.value(),
            self.suffix.args_key: self.suffix.value(),
            self.csv_uri.args_key: self.csv_uri.value(),
            self.grid_size.args_key: self.grid_size.value(),
            self.risk_eq.args_key: self.risk_eq.value(),
            self.decay_eq.args_key: self.decay_eq.value(),
            self.max_rating.args_key: self.max_rating.value(),
            self.max_stress.args_key: self.max_stress.value(),
            self.aoi_tables.args_key: self.aoi_tables.value(),
        }

        return args


class HRAPreprocessor(model.InVESTModel):
    def __init__(self):
        model.InVESTModel.__init__(
            self,
            label='Habitat Risk Assessment Preprocessor',
            target=hra_preprocessor.execute,
            validator=hra_preprocessor.validate,
            localdoc='../documentation/habitat_risk_assessment.html')

        self.habs_dir = inputs.File(
            args_key='habitats_dir',
            helptext=(
                "Checking this box indicates that habitats should be "
                "used as a base for overlap with provided stressors. "
                "If checked, the path to the habitat layers folder "
                "must be provided."),
            hideable=True,
            label='Calculate Risk to Habitats?',
            validator=self.validator)
        self.add_input(self.habs_dir)
        self.species_dir = inputs.File(
            args_key='species_dir',
            helptext=(
                "Checking this box indicates that species should be "
                "used as a base for overlap with provided stressors. "
                "If checked, the path to the species layers folder "
                "must be provided."),
            hideable=True,
            label='Calculate Risk to Species?',
            validator=self.validator)
        self.add_input(self.species_dir)
        self.stressor_dir = inputs.Folder(
            args_key='stressors_dir',
            helptext='This is the path to the stressors layers folder.',
            label='Stressors Layers Folder',
            validator=self.validator)
        self.add_input(self.stressor_dir)
        self.cur_lulc_box = inputs.Container(
            expandable=False,
            label='Criteria')
        self.add_input(self.cur_lulc_box)
        self.help_label = inputs.Label(
            text=(
                "(Choose at least 1 criteria for each category below, "
                "and at least 4 total.)"))
        self.exp_crit = inputs.Multi(
            args_key='exposure_crits',
            callable_=functools.partial(inputs.Text, label="Input Criteria"),
            label='Exposure',
            link_text='Add Another')
        self.cur_lulc_box.add_input(self.exp_crit)
        self.sens_crit = inputs.Multi(
            args_key='sensitivity_crits',
            callable_=functools.partial(inputs.Text, label="Input Criteria"),
            label='Consequence: Sensitivity',
            link_text='Add Another')
        self.cur_lulc_box.add_input(self.sens_crit)
        self.res_crit = inputs.Multi(
            args_key='resilience_crits',
            callable_=functools.partial(inputs.Text, label="Input Criteria"),
            label='Consequence: Resilience',
            link_text='Add Another')
        self.cur_lulc_box.add_input(self.res_crit)
        self.crit_dir = inputs.File(
            args_key='criteria_dir',
            helptext=(
                "Checking this box indicates that model should use "
                "criteria from provided shapefiles.  Each shapefile in "
                "the folder directories will need to contain a "
                "'Rating' attribute to be used for calculations in the "
                "HRA model.  Refer to the HRA User's Guide for "
                "information about the MANDATORY layout of the "
                "shapefile directories."),
            hideable=True,
            label='Use Spatially Explicit Risk Score in Shapefiles',
            validator=self.validator)
        self.add_input(self.crit_dir)

    def assemble_args(self):
        args = {
            self.workspace.args_key: self.workspace.value(),
            self.suffix.args_key: self.suffix.value(),
            self.habs_dir.args_key: self.habs_dir.value(),
            self.stressor_dir.args_key: self.stressor_dir.value(),
            self.exp_crit.args_key: self.exp_crit.value(),
            self.sens_crit.args_key: self.sens_crit.value(),
            self.res_crit.args_key: self.res_crit.value(),
            self.crit_dir.args_key: self.crit_dir.value(),
        }

        for hideable_input_name in ('habs_dir', 'species_dir', 'crit_dir'):
            hideable_input = getattr(self, hideable_input_name)
            if not hideable_input.hidden:
                args[hideable_input.args_key] = hideable_input.value()

        return args
