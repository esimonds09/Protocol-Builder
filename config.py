from configparser import ConfigParser


def config(filename='database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db


class Headers:
    def __init__(self):
        self.style = {'description_width': 'initial'}

        self.start_list = ['...', 'View', 'Add', 'Update', 'Delete']

        self.table_choice = ['...', 'Projects', 'Reagents', 'Consumables', 'Project_Standards']

        self.reagent_cols = [
            'Reagent', 'Vendor', 'Category Number', 'On Hand',
            'ug', 'Vol (uL)', 'Conc (ug/uL)', 'MW (g/mol)', 'Conc (nM)'
        ]
        self.reagent_query_cols = (
            'reagent_id', 'reagent', 'vendor', 'cat_num', 'on_hand',
            'ug', 'vol_ul', 'concentration_ugul', 'mw_gmol', 'concentration_nm'
        )
        self.consumable_cols = [
            'Item', 'Vendor', 'Category Number', 'On Hand'
        ]
        self.consumable_query_cols = (
            'item_id', 'item', 'vendor', 'cat_num', 'on_hand'
        )
        self.standard_cols = [
            'Project ID', 'Standard Name', 'Stock Conc (mg/mL)',
            'MW (g/mol)', 'Stock Conc (nM)', 'On Hand'
        ]
        self.standard_query_cols = (
            'standard_id', 'proj_id', 'standard_name', 'stock_conc_mgml',
            'mw_gmol', 'stock_conc_nm', 'on_hand'
        )
        self.project_cols = ['Project Name']
        self.project_query_cols = ['proj_id', 'proj_name']


class FixedHiPrBindCalcs:
    def __init__(self):
        self.proxi_wells = 384
        self.source_wells = 96
        self.proxi_well_vol = 6
        self.ml_ul_conv = 1000
        self.tempest_comp_one = 6
        self.tempest_comp_two = 8
        self.tempest_comp_three = 4
        self.standard_buffer_amount = 300
        self.excel_reagents = [
            ["Lysozyme 10000x", 1, "71110-5", 1, 10000],
            ["Picogreen 200x", 1, "P11496", 1, 200]
        ]



if __name__ == "__main__":
    config(filename='database.ini')

