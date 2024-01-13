# coding=UTF-8

from natcap.invest.ui import model, inputs
from natcap.invest.scenic_quality import scenic_quality


class ScenicQuality(model.InVESTModel):
    def __init__(self):
        model.InVESTModel.__init__(
            self,
            label='Scenic Quality',
            target=scenic_quality.execute,
            validator=scenic_quality.validate,
            localdoc='../documentation/scenic_quality.html')

        self.beta_only = inputs.Label(
            text=(
                "This tool is considered UNSTABLE.  Users may "
                "experience performance issues and unexpected errors."))
        self.general_tab = inputs.Container(
            interactive=True,
            label='General')
        self.add_input(self.general_tab)
        self.aoi_uri = inputs.File(
            args_key='aoi_uri',
            helptext=(
                "An OGR-supported vector file.  This AOI instructs "
                "the model where to clip the input data and the extent "
                "of analysis.  Users will create a polygon feature "
                "layer that defines their area of interest.  The AOI "
                "must intersect the Digital Elevation Model (DEM)."),
            label='Area of Interest (Vector)',
            validator=self.validator)
        self.general_tab.add_input(self.aoi_uri)
        self.cell_size = inputs.Text(
            args_key='cell_size',
            helptext='Length (in meters) of each side of the (square) cell.',
            label='Cell Size (meters)',
            validator=self.validator)
        self.general_tab.add_input(self.cell_size)
        self.structure_uri = inputs.File(
            args_key='structure_uri',
            helptext=(
                "An OGR-supported vector file.  The user must specify "
                "a point feature layer that indicates locations of "
                "objects that contribute to negative scenic quality, "
                "such as aquaculture netpens or wave energy "
                "facilities.  In order for the viewshed analysis to "
                "run correctly, the projection of this input must be "
                "consistent with the project of the DEM input."),
            label='Features Impacting Scenic Quality (Vector)',
            validator=self.validator)
        self.general_tab.add_input(self.structure_uri)
        self.dem_uri = inputs.File(
            args_key='dem_uri',
            helptext=(
                "A GDAL-supported raster file.  An elevation raster "
                "layer is required to conduct viewshed analysis. "
                "Elevation data allows the model to determine areas "
                "within the AOI's land-seascape where point features "
                "contributing to negative scenic quality are visible."),
            label='Digital Elevation Model (Raster)',
            validator=self.validator)
        self.general_tab.add_input(self.dem_uri)
        self.refraction = inputs.Text(
            args_key='refraction',
            helptext=(
                "The earth curvature correction option corrects for "
                "the curvature of the earth and refraction of visible "
                "light in air.  Changes in air density curve the light "
                "downward causing an observer to see further and the "
                "earth to appear less curved.  While the magnitude of "
                "this effect varies with atmospheric conditions, a "
                "standard rule of thumb is that refraction of visible "
                "light reduces the apparent curvature of the earth by "
                "one-seventh.  By default, this model corrects for the "
                "curvature of the earth and sets the refractivity "
                "coefficient to 0.13."),
            label='Refractivity Coefficient',
            validator=self.validator)
        self.general_tab.add_input(self.refraction)
        self.pop_uri = inputs.File(
            args_key='pop_uri',
            helptext=(
                "A GDAL-supported raster file.  A population raster "
                "layer is required to determine population within the "
                "AOI's land-seascape where point features contributing "
                "to negative scenic quality are visible and not "
                "visible."),
            label='Population (Raster)',
            validator=self.validator)
        self.general_tab.add_input(self.pop_uri)
        self.overlap_uri = inputs.File(
            args_key='overlap_uri',
            helptext=(
                "An OGR-supported vector file.  The user has the "
                "option of providing a polygon feature layer where "
                "they would like to determine the impact of objects on "
                "visual quality.  This input must be a polygon and "
                "projected in meters.  The model will use this layer "
                "to determine what percent of the total area of each "
                "polygon feature can see at least one of the point "
                "features impacting scenic quality."),
            label='Overlap Analysis Features (Vector)',
            validator=self.validator)
        self.general_tab.add_input(self.overlap_uri)
        self.valuation_tab = inputs.Container(
            interactive=True,
            label='Valuation')
        self.add_input(self.valuation_tab)
        self.valuation_function = inputs.Dropdown(
            args_key='valuation_function',
            helptext=(
                "This field indicates the functional form f(x) the "
                "model will use to value the visual impact for each "
                "viewpoint.  For distances less than 1 km (x<1), the "
                "model uses a linear form g(x) where the line passes "
                "through f(1) (i.e.  g(1) == f(1)) and extends to zero "
                "with the same slope as f(1) (i.e.  g'(x) == f'(1))."),
            label='Valuation Function',
            options=['polynomial: a + bx + cx^2 + dx^3',
                     'logarithmic: a + b ln(x)'])
        self.valuation_tab.add_input(self.valuation_function)
        self.a_coefficient = inputs.Text(
            args_key='a_coefficient',
            helptext=(
                "First coefficient used either by the polynomial or "
                "by the logarithmic valuation function."),
            label="'a' Coefficient (polynomial/logarithmic)",
            validator=self.validator)
        self.valuation_tab.add_input(self.a_coefficient)
        self.b_coefficient = inputs.Text(
            args_key='b_coefficient',
            helptext=(
                "Second coefficient used either by the polynomial or "
                "by the logarithmic valuation function."),
            label="'b' Coefficient (polynomial/logarithmic)",
            validator=self.validator)
        self.valuation_tab.add_input(self.b_coefficient)
        self.c_coefficient = inputs.Text(
            args_key='c_coefficient',
            helptext="Third coefficient for the polynomial's quadratic term.",
            label="'c' Coefficient (polynomial only)",
            validator=self.validator)
        self.valuation_tab.add_input(self.c_coefficient)
        self.d_coefficient = inputs.Text(
            args_key='d_coefficient',
            helptext="Fourth coefficient for the polynomial's cubic exponent.",
            label="'d' Coefficient (polynomial only)",
            validator=self.validator)
        self.valuation_tab.add_input(self.d_coefficient)
        self.max_valuation_radius = inputs.Text(
            args_key='max_valuation_radius',
            helptext=(
                "Radius beyond which the valuation is set to zero. "
                "The valuation function 'f' cannot be negative at the "
                "radius 'r' (f(r)>=0)."),
            label='Maximum Valuation Radius (meters)',
            validator=self.validator)
        self.valuation_tab.add_input(self.max_valuation_radius)

    def assemble_args(self):
        args = {
            self.workspace.args_key: self.workspace.value(),
            self.suffix.args_key: self.suffix.value(),
            self.aoi_uri.args_key: self.aoi_uri.value(),
            self.structure_uri.args_key: self.structure_uri.value(),
            self.dem_uri.args_key: self.dem_uri.value(),
            self.refraction.args_key: self.refraction.value(),
            self.valuation_function.args_key: self.valuation_function.value(),
            self.a_coefficient.args_key: self.a_coefficient.value(),
            self.b_coefficient.args_key: self.b_coefficient.value(),
            self.c_coefficient.args_key: self.c_coefficient.value(),
            self.d_coefficient.args_key: self.d_coefficient.value(),
            self.max_valuation_radius.args_key:
                self.max_valuation_radius.value(),
        }
        if self.cell_size.value():
            args[self.cell_size.args_key] = self.cell_size.value()
        if self.pop_uri.value():
            args[self.pop_uri.args_key] = self.pop_uri.value()
        if self.overlap_uri.value():
            args[self.overlap_uri.args_key] = self.overlap_uri.value()

        return args
