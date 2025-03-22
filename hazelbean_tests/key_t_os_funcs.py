if __name__ == '__main__':
    
    import os
    import hazelbean as hb


    run_all = 0
    remove_temporary_files = 0
    output_dir = 'data'

    test_this = 0
    if test_this or run_all:
        input_dict = {
            'row_1': {'col_1': 1, 'col_2': 2},
            'row_2': {'col_1': 3, 'col_2': 4}
        }
        df = hb.dict_to_df(input_dict)
        hb.df_to_dict(df)

        print(df)
        print('Test complete.')
    test_this = 1
    if test_this or run_all:
        input_dict = {
            'row_1': {
                'col_1': 1,
                'col_2': 2,
            },
            'row_2': {
                'col_1': 3,
                'col_2': {
                    'third_dict': {
                        'this': 'this_value',
                        'that': 3,
                        'thee other': 2,
                    },
                },
            },
            'empty_dict_row': {
            },
            'empty_list': [],
            'single_list': [
                5, 'this', 44,
            ],
            'outer_dict': {
                'mid_dict': {
                    'inner1': [
                        1, 2, 3
                    ],
                    'inner2': [
                        4, 5, 6,
                    ],
                }
            },
            '2d_lists': 
                [
                    [
                        1, 2, 3,
                    ],
                    [7, 8, 9,]
                ],
            'empty': '',
            
        }

        a = hb.describe_iterable(input_dict)
        expected_len = 840
        
        # assert a == input_dict
        b = hb.print_iterable(input_dict)

        if len(b) != expected_len:
            raise NameError('print_iterable FAILED ITS TEST!')
        
        input_str = 'tricky_string'
        a = hb.describe_iterable(input_str)
        # assert a == input_dict
        b = hb.print_iterable(input_str)





    print('Test Complete!')
    
    


