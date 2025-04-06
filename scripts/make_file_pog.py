import hazelbean as hb
import os

path = os.path.join(os.path.dirname(__file__), "../data/crops/johnson/crop_calories/maize_calories_per_ha_masked.tif")
hb.make_path_pog(path)