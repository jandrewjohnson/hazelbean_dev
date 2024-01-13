# coding=UTF-8

from natcap.invest.ui import model, inputs
from natcap.invest.coastal_vulnerability import coastal_vulnerability


class CoastalVulnerability(model.InVESTModel):
    def __init__(self):
        model.InVESTModel.__init__(
            self,
            label='Coastal Vulnerability Assessment Tool',
            target=coastal_vulnerability.execute,
            validator=coastal_vulnerability.validate,
            localdoc='../documentation/coastal_vulnerability.html',
            suffix_args_key='suffix'
        )

        self.general_tab = inputs.Container(
            interactive=True,
            label='General')
        self.add_input(self.general_tab)
        self.area_computed = inputs.Dropdown(
            args_key='area_computed',
            helptext=(
                "Determine if the output data is about all the coast "
                "or about sheltered segments only."),
            label='Output Area: Sheltered/Exposed?',
            options=['both', 'sheltered'])
        self.general_tab.add_input(self.area_computed)
        self.area_of_interest = inputs.File(
            args_key='aoi_uri',
            helptext=(
                "An OGR-supported, single-feature polygon vector "
                "file.  All outputs will be in the AOI's projection."),
            label='Area of Interest (Vector)',
            validator=self.validator)
        self.general_tab.add_input(self.area_of_interest)
        self.landmass_uri = inputs.File(
            args_key='landmass_uri',
            helptext=(
                "An OGR-supported vector file containing a landmass "
                "polygon from where the coastline will be extracted. "
                "The default is the global land polygon."),
            label='Land Polygon (Vector)',
            validator=self.validator)
        self.general_tab.add_input(self.landmass_uri)
        self.bathymetry_layer = inputs.File(
            args_key='bathymetry_uri',
            helptext=(
                "A GDAL-supported raster of the terrain elevation in "
                "the area of interest.  Used to compute depths along "
                "fetch rays, relief and surge potential."),
            label='Bathymetry Layer (Raster)',
            validator=self.validator)
        self.general_tab.add_input(self.bathymetry_layer)
        self.bathymetry_constant = inputs.Text(
            args_key='bathymetry_constant',
            helptext=(
                "Integer value between 1 and 5. If layer associated "
                "to this field is omitted, replace all shore points "
                "for this layer with a constant rank value in the "
                "computation of the coastal vulnerability index.  If "
                "both the file and value for the layer are omitted, "
                "the layer is skipped altogether."),
            label='Layer Value if Path Omitted',
            validator=self.validator)
        self.general_tab.add_input(self.bathymetry_constant)
        self.relief = inputs.File(
            args_key='relief_uri',
            helptext=(
                "A GDAL-supported raster file containing the land "
                "elevation used to compute the average land elevation "
                "within a user-defined radius (see Elevation averaging "
                "radius)."),
            label='Relief (Raster)',
            validator=self.validator)
        self.general_tab.add_input(self.relief)
        self.relief_constant = inputs.Text(
            args_key='relief_constant',
            helptext=(
                "Integer value between 1 and 5. If layer associated "
                "to this field is omitted, replace all shore points "
                "for this layer with a constant rank value in the "
                "computation of the coastal vulnerability index.  If "
                "both the file and value for the layer are omitted, "
                "the layer is skipped altogether."),
            label='Layer Value If Path Omitted',
            validator=self.validator)
        self.general_tab.add_input(self.relief_constant)
        self.cell_size = inputs.Text(
            args_key='cell_size',
            helptext=(
                "Cell size in meters.  The higher the value, the "
                "faster the computation, but the coarser the output "
                "rasters produced by the model."),
            label='Model Resolution (Segment Size)',
            validator=self.validator)
        self.general_tab.add_input(self.cell_size)
        self.depth_threshold = inputs.Text(
            args_key='depth_threshold',
            helptext=(
                "Depth in meters (integer) cutoff to determine if "
                "fetch rays project over deep areas."),
            label='Depth Threshold (meters)',
            validator=self.validator)
        self.general_tab.add_input(self.depth_threshold)
        self.exposure_proportion = inputs.Text(
            args_key='exposure_proportion',
            helptext=(
                "Minimum proportion of rays that project over exposed "
                "and/or deep areas need to classify a shore segment as "
                "exposed."),
            label='Exposure Proportion',
            validator=self.validator)
        self.general_tab.add_input(self.exposure_proportion)
        self.geomorphology_uri = inputs.File(
            args_key='geomorphology_uri',
            helptext=(
                "A OGR-supported polygon vector file that has a field "
                "called 'RANK' with values between 1 and 5 in the "
                "attribute table."),
            label='Geomorphology (Vector)',
            validator=self.validator)
        self.general_tab.add_input(self.geomorphology_uri)
        self.geomorphology_constant = inputs.Text(
            args_key='geomorphology_constant',
            helptext=(
                "Integer value between 1 and 5. If layer associated "
                "to this field is omitted, replace all shore points "
                "for this layer with a constant rank value in the "
                "computation of the coastal vulnerability index.  If "
                "both the file and value for the layer are omitted, "
                "the layer is skipped altogether."),
            label='Layer Value if Path Omitted',
            validator=self.validator)
        self.general_tab.add_input(self.geomorphology_constant)
        self.habitats_directory_uri = inputs.Folder(
            args_key='habitats_directory_uri',
            helptext=(
                "Directory containing OGR-supported polygon vectors "
                "associated with natural habitats.  The name of these "
                "shapefiles should be suffixed with the ID that is "
                "specified in the natural habitats CSV file provided "
                "along with the habitats."),
            label='Natural Habitats Directory',
            validator=self.validator)
        self.general_tab.add_input(self.habitats_directory_uri)
        self.habitats_csv_uri = inputs.File(
            args_key='habitats_csv_uri',
            helptext=(
                "A CSV file listing the attributes for each habitat. "
                "For more information, see 'Habitat Data Layer' "
                "section in the model's documentation.</a>."),
            interactive=False,
            label='Natural Habitats Table (CSV)',
            validator=self.validator)
        self.general_tab.add_input(self.habitats_csv_uri)
        self.habitats_constant = inputs.Text(
            args_key='habitat_constant',
            helptext=(
                "Integer value between 1 and 5. If layer associated "
                "to this field is omitted, replace all shore points "
                "for this layer with a constant rank value in the "
                "computation of the coastal vulnerability index.  If "
                "both the file and value for the layer are omitted, "
                "the layer is skipped altogether."),
            label='Layer Value if Path Omitted',
            validator=self.validator)
        self.general_tab.add_input(self.habitats_constant)
        self.climatic_forcing_uri = inputs.File(
            args_key='climatic_forcing_uri',
            helptext=(
                "An OGR-supported vector containing both wind and "
                "wave information across the region of interest."),
            label='Climatic Forcing Grid (Vector)',
            validator=self.validator)
        self.general_tab.add_input(self.climatic_forcing_uri)
        self.climatic_forcing_constant = inputs.Text(
            args_key='climatic_forcing_constant',
            helptext=(
                "Integer value between 1 and 5. If layer associated "
                "to this field is omitted, replace all shore points "
                "for this layer with a constant rank value in the "
                "computation of the coastal vulnerability index.  If "
                "both the file and value for the layer are omitted, "
                "the layer is skipped altogether."),
            label='Layer Value if Path Omitted',
            validator=self.validator)
        self.general_tab.add_input(self.climatic_forcing_constant)
        self.continental_shelf_uri = inputs.File(
            args_key='continental_shelf_uri',
            helptext=(
                "An OGR-supported polygon vector delineating the "
                "edges of the continental shelf.  Default is global "
                "continental shelf shapefile.  If omitted, the user "
                "can specify depth contour.  See entry below."),
            label='Continental Shelf (Vector)',
            validator=self.validator)
        self.general_tab.add_input(self.continental_shelf_uri)
        self.depth_contour = inputs.Text(
            args_key='depth_contour',
            helptext=(
                "Used to delineate shallow and deep areas. "
                "Continental shelf limit is at about 150 meters."),
            label='Depth Countour Level (meters)',
            validator=self.validator)
        self.general_tab.add_input(self.depth_contour)
        self.sea_level_rise_uri = inputs.File(
            args_key='sea_level_rise_uri',
            helptext=(
                "An OGR-supported point or polygon vector file "
                "containing features with 'Trend' fields in the "
                "attributes table."),
            label='Sea Level Rise (Vector)',
            validator=self.validator)
        self.general_tab.add_input(self.sea_level_rise_uri)
        self.sea_level_rise_constant = inputs.Text(
            args_key='sea_level_rise_constant',
            helptext=(
                "Integer value between 1 and 5. If layer associated "
                "to this field is omitted, replace all shore points "
                "for this layer with a constant rank value in the "
                "computation of the coastal vulnerability index.  If "
                "both the file and value for the layer are omitted, "
                "the layer is skipped altogether."),
            label='Layer Value if Path Omitted',
            validator=self.validator)
        self.general_tab.add_input(self.sea_level_rise_constant)
        self.structures_uri = inputs.File(
            args_key='structures_uri',
            helptext=(
                "An OGR-supported vector file containing rigid "
                "structures used to identify the portions of the coast "
                "that is armored."),
            label='Structures (Vectors)',
            validator=self.validator)
        self.general_tab.add_input(self.structures_uri)
        self.structures_constant = inputs.Text(
            args_key='structures_constant',
            helptext=(
                "Integer value between 1 and 5. If layer associated "
                "to this field is omitted, replace all shore points "
                "for this layer with a constant rank value in the "
                "computation of the coastal vulnerability index.  If "
                "both the file and value for the layer are omitted, "
                "the layer is skipped altogether."),
            label='Layer Value if Path Omitted',
            validator=self.validator)
        self.general_tab.add_input(self.structures_constant)
        self.population_uri = inputs.File(
            args_key='population_uri',
            helptext=(
                'A GDAL-supported raster file representing the population '
                'density.'),
            label='Population Layer (Raster)',
            validator=self.validator)
        self.general_tab.add_input(self.population_uri)
        self.urban_center_threshold = inputs.Text(
            args_key='urban_center_threshold',
            helptext=(
                "Minimum population required to consider the shore "
                "segment a population center."),
            label='Min. Population in Urban Centers',
            validator=self.validator)
        self.general_tab.add_input(self.urban_center_threshold)
        self.additional_layer_uri = inputs.File(
            args_key='additional_layer_uri',
            helptext=(
                "An OGR-supported vector file representing sea level "
                "rise, and will be used in the computation of coastal "
                "vulnerability and coastal vulnerability without "
                "habitat."),
            label='Additional Layer (Vector)',
            validator=self.validator)
        self.general_tab.add_input(self.additional_layer_uri)
        self.additional_layer_constant = inputs.Text(
            args_key='additional_layer_constant',
            helptext=(
                "Integer value between 1 and 5. If layer associated "
                "to this field is omitted, replace all shore points "
                "for this layer with a constant rank value in the "
                "computation of the coastal vulnerability index.  If "
                "both the file and value for the layer are omitted, "
                "the layer is skipped altogether."),
            label='Layer Value if Path Omitted',
            validator=self.validator)
        self.general_tab.add_input(self.additional_layer_constant)
        self.advanced_tab = inputs.Container(
            interactive=True,
            label='Advanced')
        self.add_input(self.advanced_tab)
        self.elevation_averaging_radius = inputs.Text(
            args_key='elevation_averaging_radius',
            helptext=(
                "Distance in meters (integer). Each pixel average "
                "elevation will be computed within this radius."),
            label='Elevation Averaging Radius (meters)',
            validator=self.validator)
        self.advanced_tab.add_input(self.elevation_averaging_radius)
        self.mean_sea_level_datum = inputs.Text(
            args_key='mean_sea_level_datum',
            helptext=(
                "Height in meters (integer). This input is the "
                "elevation of Mean Sea Level (MSL) datum relative to "
                "the datum of the bathymetry layer.  The model "
                "transforms all depths to MSL datum.  A positive value "
                "means the MSL is higher than the bathymetry's zero "
                "(0) elevation, so the value is subtracted from the "
                "bathymetry."),
            label='Mean Sea Level Datum (meters)',
            validator=self.validator)
        self.advanced_tab.add_input(self.mean_sea_level_datum)
        self.rays_per_sector = inputs.Text(
            args_key='rays_per_sector',
            helptext=(
                "Number of rays used to subsample the fetch distance "
                "within each of the 16 sectors."),
            label='Rays per Sector',
            validator=self.validator)
        self.advanced_tab.add_input(self.rays_per_sector)
        self.max_fetch = inputs.Text(
            args_key='max_fetch',
            helptext=(
                'Maximum fetch distance computed by the model '
                '(&gt;=60,000m).'),
            label='Maximum Fetch Distance (meters)',
            validator=self.validator)
        self.advanced_tab.add_input(self.max_fetch)
        self.spread_radius = inputs.Text(
            args_key='spread_radius',
            helptext=(
                "Integer multiple of 'cell size'. The coast from the "
                "geomorphology layer could be of a better resolution "
                "than the global landmass, so the shores do not "
                "necessarily overlap.  To make them coincide, the "
                "shore from the geomorphology layer is widened by 1 or "
                "more pixels.  The value should be a multiple of 'cell "
                "size' that indicates how many pixels the coast from "
                "the geomorphology layer is widened.  The widening "
                "happens on each side of the coast (n pixels landward, "
                "and n pixels seaward)."),
            label='Coastal Overlap (meters)',
            validator=self.validator)
        self.advanced_tab.add_input(self.spread_radius)
        self.population_radius = inputs.Text(
            args_key='population_radius',
            helptext=(
                "Radius length in meters used to count the number of "
                "people leaving close to the coast."),
            label='Coastal Neighborhood (radius in meters)',
            validator=self.validator)
        self.advanced_tab.add_input(self.population_radius)

        # Set interactivity, requirement as input sufficiency changes
        self.habitats_directory_uri.sufficiency_changed.connect(
            self.habitats_csv_uri.set_interactive)

    def assemble_args(self):
        args = {
            self.workspace.args_key: self.workspace.value(),
            self.suffix.args_key: self.suffix.value(),
            self.area_computed.args_key: self.area_computed.value(),
            self.area_of_interest.args_key: self.area_of_interest.value(),
            self.landmass_uri.args_key: self.landmass_uri.value(),
            self.cell_size.args_key: self.cell_size.value(),
            self.exposure_proportion.args_key: self.exposure_proportion.value(),
            self.habitats_csv_uri.args_key: self.habitats_csv_uri.value(),
            self.population_uri.args_key: self.population_uri.value(),
            self.urban_center_threshold.args_key: (
                self.urban_center_threshold.value()),
            self.rays_per_sector.args_key: self.rays_per_sector.value(),
            self.spread_radius.args_key: self.spread_radius.value(),
            self.population_radius.args_key: self.population_radius.value(),
            self.bathymetry_layer.args_key: self.bathymetry_layer.value(),
            self.relief.args_key: self.relief.value(),
        }
        if self.bathymetry_constant.value():
            args[self.bathymetry_constant.args_key] = (
                self.bathymetry_constant.value())
        if self.relief_constant.value():
            args[self.relief_constant.args_key] = self.relief_constant.value()
        if self.depth_threshold.value():
            args[self.depth_threshold.args_key] = self.depth_threshold.value()
        if self.geomorphology_uri.value():
            args[self.geomorphology_uri.args_key] = (
                self.geomorphology_uri.value())
        if self.geomorphology_constant.value():
            args[self.geomorphology_constant.args_key] = self.geomorphology_constant.value()
        if self.habitats_directory_uri.value():
            args[self.habitats_directory_uri.args_key] = self.habitats_directory_uri.value()
        if self.habitats_constant.value():
            args[self.habitats_constant.args_key] = self.habitats_constant.value()
        if self.climatic_forcing_uri.value():
            args[self.climatic_forcing_uri.args_key] = self.climatic_forcing_uri.value()
        if self.climatic_forcing_constant.value():
            args[self.climatic_forcing_constant.args_key] = self.climatic_forcing_constant.value()
        if self.continental_shelf_uri.value():
            args[self.continental_shelf_uri.args_key] = self.continental_shelf_uri.value()
        if self.depth_contour.value():
            args[self.depth_contour.args_key] = self.depth_contour.value()
        if self.sea_level_rise_uri.value():
            args[self.sea_level_rise_uri.args_key] = self.sea_level_rise_uri.value()
        if self.sea_level_rise_constant.value():
            args[self.sea_level_rise_constant.args_key] = self.sea_level_rise_constant.value()
        if self.structures_uri.value():
            args[self.structures_uri.args_key] = self.structures_uri.value()
        if self.structures_constant.value():
            args[self.structures_constant.args_key] = self.structures_constant.value()
        if self.additional_layer_uri.value():
            args[self.additional_layer_uri.args_key] = self.additional_layer_uri.value()
        if self.additional_layer_constant.value():
            args[self.additional_layer_constant.args_key] = self.additional_layer_constant.value()
        if self.elevation_averaging_radius.value():
            args[self.elevation_averaging_radius.args_key] = self.elevation_averaging_radius.value()
        if self.mean_sea_level_datum.value():
            args[self.mean_sea_level_datum.args_key] = self.mean_sea_level_datum.value()
        if self.max_fetch.value():
            args[self.max_fetch.args_key] = self.max_fetch.value()

        return args
