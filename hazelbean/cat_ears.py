# coding=utf-8

import os, sys, json, shutil
from collections import OrderedDict

import pandas as pd
import hazelbean as hb

def parse_to_ce_list(input_string):
    """Return a list with cat-eared elements in order. """
    to_return = []
    ls = input_string.split('<')
    if len(ls) == 1: # If there are no cat ears, just return the  string.
        to_return = hb.convert_string_to_implied_type(ls[0])
    elif len(ls) > 1:
        for i in range(len(ls)):
            if len(ls[i]) > 0:
                if i == 0 and ls[i][0] != '<':
                    to_return.append(hb.convert_string_to_implied_type(ls[i]))
                elif len(ls[i]) > 2:
                    if ls[i][0] == '^' and ls[i][1] == '>':
                        to_return.append(hb.convert_string_to_implied_type(ls[i][2:]))
                    elif ls[i][0] == '^' and ls[i][1] != '>':
                        ls2 = ls[i].split('^')
                        to_return.append({hb.convert_string_to_implied_type(ls2[1]):hb.convert_string_to_implied_type(ls2[2][1:])})

                elif len(ls[i]) == 1:
                    to_return.append(hb.convert_string_to_implied_type(ls[i]))

    return to_return


def parse_cat_ears_in_string(input_string):
    """
    Custom string manipulation to identify lists or dicts in a long string, such as a R-script output.
    :param input_string: 
    :return: [List,  OrderedDict]
    """
    split = input_string.split('<^>')
    to_return = OrderedDict()

    for i, value in enumerate(split):
        if i % 3 == 1:
            key_to_return = value
        elif i % 3 == 2:
            value_to_return = value
            to_return[key_to_return] = value_to_return

    ## This is the fuller version, benched for now
    # to_return = [list(), OrderedDict()]
    #
    # for i, s1 in enumerate(first_split):
    #     if s1[0] == '>': # Simple split
    #         if i + 1 < len(first_split):  # Ensure we don't consider past end of the string.
    #             first_split[i + 1] = first_split[i + 1][1:] # remove the '>' from the next result
    #             to_return[0].append(s1)
    #     elif s1[0] == ' ': # Then it is a key-value pair.
    #         j = 1 # NOT ZERO, next thing is desired.
    #         current_var_name_string = ''
    #         while(j < 9999999999999): # Check the next characters
    #             if i + j < len(s1): # Ensure we don't consider past end of the string.
    #                 if s1[j] != '>':
    #                     current_var_name_string += s1[j]
    #                 if s1[j] is '^' and s1[j + 1] is '>':
    #                     current_value_string = s1[0: j-1]
    #                     if len(current_var_name_string) > 0:
    #                         if len(current_value_string) > 0: # Then it's a key value pair
    #                             first_split[i + 1] = first_split[i + 1][1:]  # remove the '^>' from the next result
    #                             to_return[1][current_var_name_string] = current_value_string
    #                             break
    #                         else:
    #                             raise Exception('length of current_value_string was zero. This type of catear is not yet supported.')
    #                     else:
    #                         raise Exception('length of current_value_string was zero. This type of catear is not yet supported.')
    #             j += 1

    return to_return









def get_combined_list(input_string):
    return_list = []
    ce_list = parse_to_ce_list(input_string)
    for i in ce_list:
        if type(i) is not dict:
            return_list.append(i)

    return return_list

def get_combined_odict(input_string):
    return_odict = OrderedDict()
    ce_list = parse_to_ce_list(input_string)
    for i in ce_list:
        if type(i) is dict:
            for j in i.keys():
                return_odict[j] = i[j]

    return return_odict


def collapse_ce_list(input_string):
    return_list = []
    ce_list = parse_to_ce_list(input_string)
    last_type = None
    new_list = None
    new_odict = None
    for c, i in enumerate(ce_list):
        if type(i) is not dict and last_type is not list:
            new_list = [i]
            return_list.append(new_list)
            last_type = list
        elif type(i) is not dict:
            new_list.append(i)
        elif type(i) is dict and last_type is not dict:
            new_odict = OrderedDict()
            return_list.append(new_odict)
            for j in i.keys():
                new_odict[j] = i[j]
            last_type = dict
        elif type(i) is dict:
            for j in i.keys():
                new_odict[j] = i[j]

    return return_list

