import hazelbean as hb

equation = """
depvar ~ mask(indvar_1, is_iindvar_1, [1, 2]) + indvar_2 + indvar_3 + indvar_4 + indvar_1 * indvar_3 + log(indvar_1) + indvar_2 ^ 2 + indvar_3 * 2 + dummy(indvar_5, indvar_5_is_cropland, [10,20])

"""

from hazelbean.stats import *
r = parse_equation_to_dict(equation)
print(r)

print('Test complete.')



