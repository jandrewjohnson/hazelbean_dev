# coding=UTF-8

from natcap.invest.ui import model, inputs
import natcap.invest.scenario_gen_proximity
import natcap.invest.scenario_generator.scenario_generator

from osgeo import ogr


class ScenarioGenProximity(model.InVESTModel):
    def __init__(self):
        model.InVESTModel.__init__(
            self,
            label='Scenario Generator: Proximity Based',
            target=natcap.invest.scenario_gen_proximity.execute,
            validator=natcap.invest.scenario_gen_proximity.validate,
            localdoc='../documentation/scenario_gen_proximity.html')

        self.base_lulc_path = inputs.File(
            args_key='base_lulc_path',
            label='Base Land Use/Cover (Raster)',
            validator=self.validator)
        self.add_input(self.base_lulc_path)
        self.aoi_path = inputs.File(
            args_key='aoi_path',
            helptext=(
                "This is a set of polygons that will be used to "
                "aggregate carbon values at the end of the run if "
                "provided."),
            label='Area of interest (Vector) (optional)',
            validator=self.validator)
        self.add_input(self.aoi_path)
        self.area_to_convert = inputs.Text(
            args_key='area_to_convert',
            label='Max area to convert (Ha)',
            validator=self.validator)
        self.add_input(self.area_to_convert)
        self.focal_landcover_codes = inputs.Text(
            args_key='focal_landcover_codes',
            label='Focal Landcover Codes (list)',
            validator=self.validator)
        self.add_input(self.focal_landcover_codes)
        self.convertible_landcover_codes = inputs.Text(
            args_key='convertible_landcover_codes',
            label='Convertible Landcover Codes (list)',
            validator=self.validator)
        self.add_input(self.convertible_landcover_codes)
        self.replacment_lucode = inputs.Text(
            args_key='replacment_lucode',
            label='Replacement Landcover Code (int)',
            validator=self.validator)
        self.add_input(self.replacment_lucode)
        self.convert_farthest_from_edge = inputs.Checkbox(
            args_key='convert_farthest_from_edge',
            helptext=(
                "This scenario converts the convertible landcover "
                "codes starting at the furthest pixel from the closest "
                "base landcover codes and moves inward."),
            label='Farthest from edge')
        self.add_input(self.convert_farthest_from_edge)
        self.convert_nearest_to_edge = inputs.Checkbox(
            args_key='convert_nearest_to_edge',
            helptext=(
                "This scenario converts the convertible landcover "
                "codes starting at the closest pixel in the base "
                "landcover codes and moves outward."),
            label='Nearest to edge')
        self.add_input(self.convert_nearest_to_edge)
        self.n_fragmentation_steps = inputs.Text(
            args_key='n_fragmentation_steps',
            helptext=(
                "This parameter is used to divide the conversion "
                "simulation into equal subareas of the requested max "
                "area.  During each sub-step the distance transform is "
                "recalculated from the base landcover codes.  This can "
                "affect the final result if the base types are also "
                "convertible types."),
            label='Number of Steps in Conversion',
            validator=self.validator)
        self.add_input(self.n_fragmentation_steps)

    def assemble_args(self):
        args = {
            self.workspace.args_key: self.workspace.value(),
            self.suffix.args_key: self.suffix.value(),
            self.base_lulc_path.args_key: self.base_lulc_path.value(),
            self.aoi_path.args_key: self.aoi_path.value(),
            self.area_to_convert.args_key: self.area_to_convert.value(),
            self.focal_landcover_codes.args_key:
                self.focal_landcover_codes.value(),
            self.convertible_landcover_codes.args_key:
                self.convertible_landcover_codes.value(),
            self.replacment_lucode.args_key: self.replacment_lucode.value(),
            self.convert_farthest_from_edge.args_key:
                self.convert_farthest_from_edge.value(),
            self.convert_nearest_to_edge.args_key:
                self.convert_nearest_to_edge.value(),
            self.n_fragmentation_steps.args_key:
                self.n_fragmentation_steps.value(),
        }

        return args


class ScenarioGenerator(model.InVESTModel):
    def __init__(self):
        model.InVESTModel.__init__(
            self,
            label='Scenario Generator',
            target=natcap.invest.scenario_generator.scenario_generator.execute,
            validator=natcap.invest.scenario_generator.scenario_generator.validate,
            localdoc='../documentation/scenario_generator.html',
            suffix_args_key='suffix',
        )
        self.landcover = inputs.File(
            args_key='landcover',
            helptext='A GDAL-supported raster file representing land-use/land-cover.',
            label='Land Cover (Raster)',
            validator=self.validator)
        self.add_input(self.landcover)
        self.transition = inputs.File(
            args_key='transition',
            helptext=(
                "This table contains the land-cover transition "
                "likelihoods, priority of transitions, area change, "
                "proximity suitiblity, proximity effect distance, seed "
                "size, short name, and patch size."),
            label='Transition Table (CSV)',
            validator=self.validator)
        self.add_input(self.transition)
        self.calculate_priorities = inputs.Checkbox(
            args_key='calculate_priorities',
            helptext=(
                "This option enables calculation of the land-cover "
                "priorities using analytical hierarchical processing. "
                "A matrix table must be entered below.  Optionally, "
                "the priorities can manually be entered in the "
                "priority column of the land attributes table."),
            interactive=False,
            label='Calculate Priorities')
        self.add_input(self.calculate_priorities)
        self.priorities_csv_uri = inputs.File(
            args_key='priorities_csv_uri',
            helptext=(
                "This table contains a matrix of land-cover type "
                "pairwise priorities used to calculate land-cover "
                "priorities."),
            interactive=False,
            label='Priorities Table (CSV)',
            validator=self.validator)
        self.add_input(self.priorities_csv_uri)
        self.calculate_proximity = inputs.Container(
            args_key='calculate_proximity',
            expandable=True,
            expanded=True,
            label='Proximity')
        self.add_input(self.calculate_proximity)
        self.calculate_transition = inputs.Container(
            args_key='calculate_transition',
            expandable=True,
            expanded=True,
            label='Specify Transitions')
        self.add_input(self.calculate_transition)
        self.calculate_factors = inputs.Container(
            args_key='calculate_factors',
            expandable=True,
            expanded=True,
            label='Use Factors')
        self.add_input(self.calculate_factors)
        self.suitability_folder = inputs.Folder(
            args_key='suitability_folder',
            label='Factors Folder',
            validator=self.validator)
        self.calculate_factors.add_input(self.suitability_folder)
        self.suitability = inputs.File(
            args_key='suitability',
            helptext=(
                "This table lists the factors that determine "
                "suitability of the land-cover for change, and "
                "includes: the factor name, layer name, distance of "
                "influence, suitability value, weight of the factor, "
                "distance breaks, and applicable land-cover."),
            label='Factors Table',
            validator=self.validator)
        self.calculate_factors.add_input(self.suitability)
        self.weight = inputs.Text(
            args_key='weight',
            helptext=(
                "The factor weight is a value between 0 and 1 which "
                "determines the weight given to the factors vs.  the "
                "expert opinion likelihood rasters.  For example, if a "
                "weight of 0.3 is entered then 30% of the final "
                "suitability is contributed by the factors and the "
                "likelihood matrix contributes 70%.  This value is "
                "entered on the tool interface."),
            label='Factor Weight',
            validator=self.validator)
        self.calculate_factors.add_input(self.weight)
        self.factor_inclusion = inputs.Dropdown(
            args_key='factor_inclusion',
            helptext='',
            interactive=False,
            label='Rasterization Method',
            options=['All touched pixels', 'Only pixels with covered center points'])
        self.calculate_factors.add_input(self.factor_inclusion)
        self.calculate_constraints = inputs.Container(
            args_key='calculate_constraints',
            expandable=True,
            label='Constraints Layer')
        self.add_input(self.calculate_constraints)
        self.constraints = inputs.File(
            args_key='constraints',
            helptext=(
                "An OGR-supported vector file.  This is a vector "
                "layer which indicates the parts of the landscape that "
                "are protected of have constraints to land-cover "
                "change.  The layer should have one field named "
                "'porosity' with a value between 0 and 1 where 0 means "
                "its fully protected and 1 means its fully open to "
                "change."),
            label='Constraints Layer (Vector)',
            validator=self.validator)
        self.calculate_constraints.add_input(self.constraints)
        self.constraints.sufficiency_changed.connect(
            self._load_colnames_constraints)
        self.constraints_field = inputs.Dropdown(
            args_key='constraints_field',
            helptext=(
                "The field from the override table that contains the "
                "value for the override."),
            interactive=False,
            options=('UNKNOWN',),
            label='Constraints Field')
        self.calculate_constraints.add_input(self.constraints_field)
        self.override_layer = inputs.Container(
            args_key='override_layer',
            expandable=True,
            expanded=True,
            label='Override Layer')
        self.add_input(self.override_layer)
        self.override = inputs.File(
            args_key='override',
            helptext=(
                "An OGR-supported vector file.  This is a vector "
                "(polygon) layer with land-cover types in the same "
                "scale and projection as the input land-cover.  This "
                "layer is used to override all the changes and is "
                "applied after the rule conversion is complete."),
            label='Override Layer (Vector)',
            validator=self.validator)
        self.override_layer.add_input(self.override)
        self.override.sufficiency_changed.connect(
            self._load_colnames_override)
        self.override_field = inputs.Dropdown(
            args_key='override_field',
            helptext=(
                "The field from the override table that contains the "
                "value for the override."),
            interactive=False,
            options=('UNKNOWN',),
            label='Override Field')
        self.override_layer.add_input(self.override_field)
        self.override_inclusion = inputs.Dropdown(
            args_key='override_inclusion',
            helptext='',
            interactive=False,
            label='Rasterization Method',
            options=['All touched pixels', 'Only pixels with covered center points'])
        self.override_layer.add_input(self.override_inclusion)
        self.seed = inputs.Text(
            args_key='seed',
            helptext=(
                "Seed must be an integer or blank.  <br/><br/>Under "
                "normal conditions, parcels with the same suitability "
                "are picked in a random order.  Setting the seed value "
                "allows the scenario generator to randomize the order "
                "in which parcels are picked, but two runs with the "
                "same seed will pick parcels in the same order."),
            label='Seed for random parcel selection (optional)',
            validator=self.validator)
        self.add_input(self.seed)

        # Set interactivity, requirement as input sufficiency changes
        self.transition.sufficiency_changed.connect(
            self.calculate_priorities.set_interactive)
        self.calculate_priorities.sufficiency_changed.connect(
            self.priorities_csv_uri.set_interactive)
        self.calculate_factors.sufficiency_changed.connect(
            self.factor_inclusion.set_interactive)
        self.constraints.sufficiency_changed.connect(
            self.constraints_field.set_interactive)
        self.override.sufficiency_changed.connect(
            self.override_field.set_interactive)
        self.override_field.sufficiency_changed.connect(
            self.override_inclusion.set_interactive)

    def _load_colnames_constraints(self, new_interactivity):
        self._load_colnames(new_interactivity,
                            self.constraints,
                            self.constraints_field)

    def _load_colnames_override(self, new_interactivity):
        self._load_colnames(new_interactivity,
                            self.override,
                            self.override_field)

    def _load_colnames(self, new_interactivity, vector_input, dropdown_input):
        if new_interactivity:
            vector_path = vector_input.value()
            vector = ogr.Open(vector_path)
            layer = vector.GetLayer()
            colnames = [defn.GetName() for defn in layer.schema]
            dropdown_input.set_options(colnames)
            dropdown_input.set_interactive(True)
        else:
            dropdown_input.set_options([])

    def assemble_args(self):
        args = {
            self.workspace.args_key: self.workspace.value(),
            self.suffix.args_key: self.suffix.value(),
            self.landcover.args_key: self.landcover.value(),
            self.transition.args_key: self.transition.value(),
            self.calculate_priorities.args_key: self.calculate_priorities.value(),
            self.priorities_csv_uri.args_key: self.priorities_csv_uri.value(),
            self.calculate_proximity.args_key: self.calculate_proximity.value(),
            self.calculate_transition.args_key: self.calculate_transition.value(),
            self.calculate_factors.args_key: self.calculate_factors.value(),
            self.calculate_constraints.args_key: self.calculate_constraints.value(),
            self.override_layer.args_key: self.override_layer.value(),
            self.seed.args_key: self.seed.value(),
        }

        if self.calculate_factors.value():
            args[self.suitability_folder.args_key] = self.suitability_folder.value()
            args[self.suitability.args_key] = self.suitability.value()
            args[self.weight.args_key] = self.weight.value()
            args[self.factor_inclusion.args_key] = self.factor_inclusion.value()

        if self.calculate_constraints.value():
            args[self.constraints.args_key] = self.constraints.value()
            args[self.constraints_field.args_key] = self.constraints_field.value()

        if self.override_layer.value():
            args[self.override.args_key] = self.override.value()
            args[self.override_field.args_key] = self.override_field.value()
            args[self.override_inclusion.args_key] = self.override_inclusion.value()

        return args
