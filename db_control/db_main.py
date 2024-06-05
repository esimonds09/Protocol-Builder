import psycopg2 as pg2
import ipywidgets as ipw
from IPython.display import display
from config import config

# This establishes the connection to the inventory_tracker database
# PARAMS = config()
# CONN = pg2.connect(**PARAMS)

# This is a global variable that can be used to style widgets
STYLE = {'description_width': 'initial'}
START_LIST = ['...', 'View', 'Add', 'Update', 'Delete']
TABLE_CHOICE = ['...', 'Projects', 'Reagents', 'Consumables', 'Project_Standards']
REAGENT_COLS = ['Reagent', 'Vendor', 'Category Number', 'On Hand', 'ug', 'Vol (uL)', 'Conc (ug/uL)', 'MW (g/mol)', 'Conc (nM)']
REAGENT_COLS_QUERY = ('reagent_id', 'reagent', 'vendor', 'cat_num', 'on_hand', 'ug', 'vol_ul', 'concentration_ugul', 'mw_gmol', 'concentration_nm')
CONSUMABLE_COLS = ['Item', 'Vendor', 'Category Number', 'On Hand']
CONSUMABLE_COLS_QUERY = ('item_id', 'item', 'vendor', 'cat_num', 'on_hand')
STANDARD_COLS = ['Project ID', 'Standard Name', 'Stock Conc (mg/mL)', 'MW (g/mol)', 'Stock Conc (nM)', 'On Hand']
STANDARD_COLS_QUERY = ('standard_id', 'proj_id', 'standard_name', 'stock_conc_mgml', 'mw_gmol', 'stock_conc_nm', 'on_hand')
PROJECT_COLS = ['Project Name']
PROJECT_COLS_QUERY = ['proj_id', 'proj_name']


class Db:
    def __init__(self, params):
        self.params = params
        self.__connect()

    def __connect(self):
        self.conn = pg2.connect(**self.params)

    def close(self):
        self.conn.close()

    def choose_project(self):
        """
        This function is called to create a select query from the database, pulling the known projects,
        creating a dictionary, and passing the dictionary back to the original function
        """
        with self.conn:
            cur = self.conn.cursor()
            select_query = f"""
            SELECT * FROM projects
            """
            cur.execute(select_query)
            data_table = cur.fetchall()
            proj_dict = {'...': 0}
            proj_dict.update({row[1]: row[0] for row in data_table})

        return proj_dict

    def update_table(self, data, table, query_header, message):
        row_to_update = []
        return_value = []
        update_count = 0
        for row in data:
            if row.children[-1].value:
                update_list = tuple([box.value for box in row.children[:-1]])
                row_to_update.append(update_list)
        with self.conn:
            cur = self.conn.cursor()
            for row in row_to_update:
                proj_dict = dict(zip(query_header.split(','), row))
                query_set = [f"{key} = '{value}'" for (key, value) in proj_dict.items()]
                set_string = ', '.join(query_set[1:])
                update_query = f"""
                    UPDATE {table.lower()}
                    SET {set_string}
                    WHERE {query_header.split(',')[0]} = {row[0]}
                    RETURNING on_hand
                """
                try:
                    cur.execute(update_query)
                except (Exception, pg2.DatabaseError) as error:
                    message_split = error.args[0].split('DETAIL:')
                    message.children = [ipw.HTML('ERROR:')] + [
                        ipw.HTML(f'{msg}') for msg in message_split
                    ]
                else:
                    message.children = [ipw.HTML('<b>Update(s) made!</b>')]
                    return_value.append(cur.fetchone()[0])
                    update_count += cur.rowcount
                    self.conn.commit()
            return return_value, update_count

    def insert_to_cons_reag(self, table, query_header, data, message):
        with self.conn:
            cur = self.conn.cursor()
            insert_query = f"""
            INSERT INTO {table.lower()} ({', '.join(query_header[1:])})
            VALUES {str(tuple([box.value for box in data]))}
            """
            try:
                cur.execute(insert_query)
            except (Exception, pg2.DatabaseError) as error:
                message_split = error.args[0].split('DETAIL:')
                message.children = [ipw.HTML('ERROR:')] + [
                    ipw.HTML(f'{message}') for message in message_split
                ]
            else:
                self.conn.commit()
                message.children = [ipw.HTML(f'{table} added!</b>')]

    def insert_to_standards(self, table, project, data, message):
        with self.conn:
            insert_values = [box.value for box in data]
            insert_values.insert(0, project)
            cur = self.conn.cursor()
            insert_query = f"""
                INSERT INTO {table.lower()} ({', '.join(STANDARD_COLS_QUERY[1:])})
                VALUES {str(tuple(insert_values))}
            """
            try:
                cur.execute(insert_query)
            except (Exception, pg2.DatabaseError) as error:
                message_split = error.args[0].split('DETAIL:')
                message.children = [ipw.HTML('ERROR:')] + [
                    ipw.HTML(f'{message}') for message in message_split
                ]
            else:
                self.conn.commit()
                message.children = [ipw.HTML(f'Project standard added!</b>')]

    def add_insert_to_projects(self, proj_type, table, project, data, reagent_data, message):
        with self.conn:
            cur = self.conn.cursor()
            if proj_type == 'New':
                proj_name = data.children[0].value
                insert_query = f"""
                    INSERT INTO projects (proj_name)
                    VALUES ('{proj_name}')
                    RETURNING proj_id
                """
                try:
                    cur.execute(insert_query)
                except (Exception, pg2.DatabaseError) as error:
                    message_split = error.args[0].split('DETAIL:')
                    message.children = [ipw.HTML('ERROR:')] + [
                        ipw.HTML(f'{message}') for message in message_split
                    ]
                    proj_id = None
                else:
                    proj_id = cur.fetchone()[0]
                    self.conn.commit()
            else:
                proj_id = project
            if not proj_id:
                pass
            else:
                row_to_add = []
                for Hbox in reagent_data:
                    if Hbox.children[-1].value:
                        add_list = tuple(
                            [proj_id] +
                            [Hbox.children[0].value] +
                            [box.value for box in Hbox.children[-3:-1]]
                        )
                        row_to_add.append(add_list)

                for row in row_to_add:
                    insert_query = f"""
                        INSERT INTO project_reagents (proj_id, reagent_id, assay_id, desired_conc)
                        VALUES {str(row)}
                    """
                    try:
                        cur.execute(insert_query)
                    except (Exception, pg2.DatabaseError) as error:
                        message_split = error.args[0].split('DETAIL:')
                        message.children = [ipw.HTML('ERROR:')] + [
                            ipw.HTML(f'{message}') for message in message_split
                        ]
                    else:
                        self.conn.commit()
                        message.children = [ipw.HTML(f'{table} added/updated!</b>')]

    def delete_data(self, table, data, message):
        with self.conn:
            cur = self.conn.cursor()
            pk_id = PROJECT_COLS_QUERY[0] if table == 'Projects' else REAGENT_COLS_QUERY[0] \
                if table == 'Reagents' else CONSUMABLE_COLS_QUERY[0] \
                if table == 'Consumables' else STANDARD_COLS_QUERY[0] \
                if table == 'Project_Standards' else ""

            row_to_delete = []
            for Hbox in data:
                if Hbox.children[-1].value:
                    delete_list = tuple([box.value for box in Hbox.children[:-1]])
                    row_to_delete.append(delete_list)
            for row in row_to_delete:
                insert_query = f"""
                    DELETE FROM {table}
                    WHERE {pk_id} = {row[0]}
                """
                try:
                    cur.execute(insert_query)
                except (Exception, pg2.DatabaseError) as error:
                    message_split = error.args[0].split('DETAIL:')
                    message.children = [ipw.HTML('ERROR:')] + [
                        ipw.HTML(f'{message}') for message in message_split
                    ]
                else:
                    self.conn.commit()
                    message.children = [
                        ipw.HTML(f'Sorry! Still under construction ¯\_(ツ)_/¯ </b>')]

    def query_call(self, query):
        with self.conn:
            cur = self.conn.cursor()
            cur.execute(query)
            if 'SELECT' in query:
                data = cur.fetchall()
                return data


class DbControl:
    """
    This class is responsible for the front-end inventory tracking form (inventory_form.ipynb).
    Using the pyscopg2 package, queries are run to update, add to, and show inventory.

    """
    def __init__(self):
        # self.cur = CONN.cursor()
        self.params = config()
        self.db = Db(self.params)
        # Data Table to show
        self.data_table = []
        self.existing_data_table = []
        self.query_header = None

        # TODO initialize the input and output form section skeletons here
        """ BUTTONS AND EVENTS"""
        # Button to capture inputs

        self.updates_button = ipw.Button(
            description='Update',
            button_style='info',
            style=STYLE
        )
        self.updates_button.on_click(self.capture_updates)

        self.reset_button = ipw.Button(
            description='Reset',
            button_style='warning'
        )
        self.reset_button.on_click(self.reset)

        """ FORM SKELETON """
        self.out_display = ipw.Output()
        self.input_wdgt_container = ipw.VBox()
        self.output_heading_container = ipw.VBox()
        self.output_table_container = ipw.VBox()
        self.add_reagents_container = ipw.VBox()
        self.current_reagents_container = ipw.VBox()
        self.update_message_container = ipw.VBox()

        self.input_section_container = ipw.VBox([
            ipw.HTML("<h2>Inventory Tracker</h2>"),
            ipw.HTML("<hr style='background-color:black;'>"),
            ipw.HTML("<h3>Input Section</h3>"),
            ipw.HTML("<hr style='background-color:black;'>"),
            self.input_wdgt_container,
            ipw.HTML('<br>'),
            # self.capture_inputs_button,
            self.out_display
        ])
        self.output_section_container = ipw.VBox([
            ipw.HTML("<h3>Output Section</h3>"),
            ipw.HTML("<hr style='background-color:black;'>"),
            self.output_heading_container,
            self.output_table_container,
            self.current_reagents_container,
            self.add_reagents_container,
            ipw.HTML('<br>'),
            ipw.HBox([
                self.updates_button,
                self.reset_button
            ]),
            self.update_message_container
        ])
        self.form_sections_container = ipw.VBox([
            self.input_section_container,
            self.output_section_container
        ])
        # display(self.form_sections_container)
        display(self.form_sections_container)
        self.initialize_input_section()

        # TODO Create method that initializes the widgets within skeleton
    def initialize_input_section(self):
        """
        INPUT SECTION 
        """
        def capture_inputs(event):
            if '...' in [start_menu.value, table_choice.value]:
                message = ipw.HTML('Please choose both a start option and table choice!')
            elif table_choice.value in ["Projects", "Project_Standards"] and start_menu.value == "Add":
                if table_choice.value == "Projects" and proj_type.value == '...':
                    message = ipw.HTML('Please choose new or existing!')
                elif project_choice.label == '...' and proj_type.value != 'New':
                    message = ipw.HTML('Please choose a project!')
                else:
                    message = ipw.HTML('Inputs selected!')
            else:
                message = ipw.HTML('Inputs selected!')
                input_choices = dict(
                    option=start_menu.value,
                    table=table_choice.value,
                    p_type=proj_type.value,
                    project=project_choice.value
                )
                self.output_section(**input_choices)
            with self.out_display:
                self.out_display.clear_output()
                display(message)

        # Inventory options
        start_menu = ipw.Dropdown(
            description='Choose option:',
            options=START_LIST,
            value=START_LIST[0],
            style=STYLE
        )
        # Table choices
        table_choice = ipw.Dropdown(
            description='Choose table:',
            options=TABLE_CHOICE,
            value=TABLE_CHOICE[0],
            style=STYLE
        )

        # New or Existing project to add to
        # self.first_placeholder = ipw.VBox()
        proj_type = ipw.Dropdown(
            description='Add to:',
            options=['...', 'New', 'Existing'],
            value='...',
            style=STYLE,
            disabled=True
        )

        # Project choices
        # self.second_placeholder = ipw.VBox()
        proj_names = self.db.choose_project()
        project_choice = ipw.Dropdown(
            description='Choose project:',
            options=proj_names,
            value=proj_names['...'],
            style=STYLE,
            disabled=True
        )

        capture_inputs_button = ipw.Button(
            description='Enter Inputs',
            button_style='info',
            style=STYLE
        )
        capture_inputs_button.on_click(capture_inputs)

        self.input_wdgt_container.children = [
            ipw.HBox([
                start_menu,
                table_choice,
                ipw.VBox([
                    proj_type,
                    project_choice
                ])
            ]),
            capture_inputs_button
        ]

        def enable_dropdowns(option, table, p_type, project):
            if option == 'Add' and table in ["Projects", "Project_Standards"]:
                if table == "Projects" and p_type == "...":
                    proj_type.disabled = False
                    project_choice.value = proj_names['...']
                    project_choice.disabled = True
                elif table == "Projects" and p_type == "Existing":
                    project_choice.disabled = False
                elif table == "Project_Standards":
                    proj_type.value = '...'
                    proj_type.disabled = True
                    project_choice.disabled = False
            elif option == 'Add' and table not in ["Projects", "Projects_Standards"]:
                proj_type.value = '...'
                proj_type.disabled = True
                project_choice.value = proj_names['...']
                project_choice.disabled = True
            else:
                proj_type.value = '...'
                proj_type.disabled = True
                project_choice.value = proj_names['...']
                project_choice.disabled = True

        ipw.interactive(enable_dropdowns, option=start_menu, table=table_choice, p_type=proj_type, project=project_choice)

    # TODO Try to put all returned query data into same output container
        # # Button to capture inputs
        # self.capture_inputs_button = ipw.Button(
        #     description='Enter Inputs',
        #     button_style='info',
        #     style=STYLE
        # )
        # self.capture_inputs_button.on_click(self.capture_inputs)

        """
        INPUT DISPLAY SECTION
        """
        # self.out_display = ipw.Output()
        # self.input_section_display = ipw.VBox([
        #     ipw.HTML("<h2>Inventory Tracker</h2>"),
        #     ipw.HTML("<hr style='background-color:black;'>"),
        #     ipw.HTML("<h3>Input Section</h3>"),
        #     ipw.HTML("<hr style='background-color:black;'>"),
        #     ipw.HBox([
        #         self.start_menu,
        #         ipw.VBox([
        #             self.table_choice,
        #             self.first_placeholder,
        #             self.second_placeholder
        #         ])
        #     ]),
        #     ipw.HTML('<br>'),
        #     self.capture_inputs_button,
        #     self.out_display
        # ])

        """
        OUTPUT SECTION
        """
        # self.updates_button = ipw.Button(
        #     description='Update',
        #     button_style='info',
        #     style=STYLE
        # )
        # self.updates_button.on_click(self.capture_updates)
        #
        # self.reset_button = ipw.Button(description='Reset', button_style='warning')
        # self.reset_button.on_click(self.reset)



        """
        OUTPUT DISPLAY SECTION
        """
        # These are placeholder boxes for output data based on inputs
        # self.output_heading_container = ipw.VBox()
        # self.output_table_container = ipw.VBox()
        # self.add_reagents_container = ipw.VBox()
        # self.current_reagents_container = ipw.VBox()
        # self.update_message_container = ipw.VBox()

        # This box contains the frame of the 'Inventory Tracker' section layout
        # self.output_section_display = ipw.VBox([
        #     ipw.HTML("<h3>Output Section</h3>"),
        #     ipw.HTML("<hr style='background-color:black;'>"),
        #     self.output_heading_container,
        #     self.output_table_container,
        #     self.current_reagents_container,
        #     self.add_reagents_container,
        #     ipw.HTML('<br>'),
        #     ipw.HBox([
        #         self.updates_button,
        #         self.reset_button
        #     ]),
        #     self.update_message_container
        # ])

        # This will call the function to initiate the form
        # self.input_section()

    def input_section(self):
        """
        This section contains an interactive input section, that will help guide the user to interface with the
        backend inventory tracking database
        """
        def update_inputs(start_choice, table_choice, type_choice):
            """
            This function within the function will handle the inputs selected by the user and update the user
            interface accordingly. This is an interactive function.
            """
            if start_choice == 'Add' and table_choice == 'Projects' and type_choice == '...':
                self.first_placeholder.children = [self.proj_type]
            elif start_choice == 'Add' and table_choice == 'Projects' and type_choice == 'Existing':
                proj_dict = self.db.choose_project()
                self.project_choice.options = proj_dict
                self.project_choice.value = proj_dict['...']
                self.second_placeholder.children = [self.project_choice]
            elif start_choice == 'Add' and table_choice == 'Projects' and type_choice == 'New':
                self.second_placeholder.children = []
            elif start_choice == 'Add' and table_choice == 'Project_Standards':
                proj_dict = self.db.choose_project()
                self.project_choice.options = proj_dict
                self.project_choice.value = proj_dict['...']
                self.second_placeholder.children = [self.project_choice]
            else:
                self.first_placeholder.children = []
                self.second_placeholder.children = []
                self.proj_type.value = '...'

        # This widget will feed live inputs into the update_inputs function
        ipw.interactive(update_inputs,
                        start_choice=self.start_menu,
                        table_choice=self.table_choice,
                        type_choice=self.proj_type
                        )
        display(self.input_section_display)

    # def capture_inputs(self, event):
    #     """
    #     This button-based function will be called on the capture_inputs_button
    #     This function will check that the necessary information has been input to continue, informing otherwise if not
    #     """
    #     with self.out_display:
    #         self.out_display.clear_output()
    #         display(ipw.HTML(f"{start_menu.value}"))
        # # display(ipw.HTML("<hr style='background-color:black'><h5>Howdy</h5>"))
        # if self.start_menu.value == 'Add' and self.table_choice.value == 'Projects' and self.proj_type.value == '...':
        #     with self.out_display:
        #         self.out_display.clear_output()
        #         display(ipw.HTML("Please choose 'New' or 'Existing'!"))
        # elif self.start_menu.value == 'Add' and self.table_choice.value == 'Projects' and self.proj_type.value == 'Existing' and self.project_choice.value == 0:
        #     with self.out_display:
        #         self.out_display.clear_output()
        #         display(ipw.HTML('Please choose a project!'))
        # elif self.start_menu.value != '...' and self.table_choice.value != '...':
        #     with self.out_display:
        #         self.out_display.clear_output()
        #         self.start_menu.disabled = True
        #         self.table_choice.disabled = True
        #         self.proj_type.disabled = True
        #         self.project_choice.disabled = True
        #         self.output_table_container.children = []
        #         self.output_section()
        # else:
        #     with self.out_display:
        #         self.out_display.clear_output()
        #         display(ipw.HTML('Please choose both an option and table to work with!'))

    def output_section(self, option, table, p_type, project):

        # TODO just send through dictionary -- direct to method and return 'list' which will replace self.output_cont
        """
        This function will direct the output information to a specific function based on the given input information
        """
        self.output_heading_container.children = [ipw.HTML(f"""
            Let's {option.lower()} 
            {'to' if option.lower() == 'Add' else 'our'} 
            {table.lower()}
        """)]

        if option in ('Update', 'Delete', 'View'):
            self.update_data()
        elif option == 'Add' and table in ['Projects', 'Project_Standards']:
            self.add_data_to_proj()
        elif option == 'Add':
            self.add_data()
        elif option == 'Delete':
            pass

        # self.output_heading_container.children = [ipw.HTML(f"""
        #     Let's {self.start_menu.value.lower()}
        #     {'to' if self.start_menu.value.lower() == 'Add' else 'our'}
        #     {self.table_choice.value.lower()}
        # """)]
        #
        # if self.start_menu.value in ('Update', 'Delete', 'View'):
        #     self.update_data()
        # elif self.start_menu.value == 'Add' and self.table_choice.value in ['Projects', 'Project_Standards']:
        #     self.add_data_to_proj()
        # elif self.start_menu.value == 'Add':
        #     self.add_data()
        # elif self.start_menu.value == 'Delete':
        #     pass
        # display(self.output_section_display)

    def reset(self, event):
        """
        This function will reset all the boxes and placeholders, as well as re-enable disabled input boxes
        """
        self.initialize_input_section()
        # self.out_display.clear_output()
        # self.start_menu.value = '...'
        # self.start_menu.disabled = False
        # self.table_choice.value = '...'
        # self.table_choice.disabled = False
        # self.proj_type.value = '...'
        # self.proj_type.disabled = False
        # self.project_choice.disabled = False
        # self.first_placeholder.children = []
        # self.second_placeholder.children = []
        # self.output_table_container.children = []
        # self.current_reagents_container.children = []
        # self.add_reagents_container.children = []
        # self.update_message_container.children = []

    def add_data(self):
        """
        This function will insert new data into reagents and consumables
        This function requires column headers
        """
        # Input boxes to capture add data will show in output table
        if self.table_choice.value == 'Reagents':
            header = REAGENT_COLS
            self.query_header = REAGENT_COLS_QUERY
        elif self.table_choice.value == 'Consumables':
            header = CONSUMABLE_COLS
            self.query_header = CONSUMABLE_COLS_QUERY
        else:
            header = ""

        self.output_table_container.children = [
            ipw.Text(
                description=f"{name}:",
                style={'description_width': '150px'},
                layout=ipw.Layout(width='400px')
            ) for name in header
        ]

    def add_data_to_proj(self):
        if self.table_choice.value == 'Projects' and self.proj_type.value == 'New':
            # Create text box to enter new project name
            self.output_table_container.children = [
                ipw.Text(
                    description='Add project name: ',
                    style={'description_width': '150px'},
                    layout=ipw.Layout(width='400px')
                )
            ]

            # Create list of reagents for user to choose and add to new project
            select_query = f"""
            SELECT reagent_id, reagent, on_hand FROM reagents
            """
            data_table = self.db.query_call(select_query)
            # self.cur.execute(select_query)
            # data_table = self.cur.fetchall()
            data_table.insert(0, ['Reagent_id', 'Reagent', 'On Hand'])
            conv_data = []
            for row in data_table[:1]:
                row = list(row) + ['Assay', 'Desired Conc', 'Add']
                conv_data.append(row)
            for row in data_table[1:]:
                row = list(row) + [0, 0, False]
                conv_data.append(row)

            self.add_reagents_container.children = [
                ipw.HBox([
                    ipw.HTML(value=f'<b>{str(row_item[i])}</b>',
                             layout=ipw.Layout(
                                 width='10%',
                                 border='solid'),
                             disabled=True)
                    if 'id' in str(row_item[0]) else
                    ipw.Checkbox(value=row_item[i],
                                 indent=False,
                                 layout=ipw.Layout(
                                     width='10%',
                                     border='0.5px solid'))
                    if isinstance(row_item[i], bool) else
                    ipw.Text(value=str(row_item[i]),
                             layout=ipw.Layout(
                                 width='10%',
                                 border='0.5px solid'),
                             disabled=False)
                    for i in range(0, len(row_item))
                ]) for row_item in conv_data
            ]

        # Addition of reagents to an existing project
        elif self.proj_type.value == 'Existing':
            # Selects current reagents from the existing project
            select_query = f"""
            SELECT reagents.reagent_id, reagent, on_hand, project_reagents.assay_id, project_reagents.desired_conc FROM reagents
            INNER JOIN project_reagents
            ON project_reagents.reagent_id = reagents.reagent_id
            WHERE project_reagents.proj_id = {self.project_choice.value}            
            """
            existing_table = self.db.query_call(select_query)
            # self.cur.execute(select_query)
            # existing_table = self.cur.fetchall()
            existing_table.insert(0, ['Reagent_id', 'Reagent', 'On Hand', 'Assay', 'Desired Conc'])
            self.current_reagents_container.children = [
                ipw.HBox([
                    ipw.HTML(value=f'<b>{str(row_item[i])}</b>',
                             layout=ipw.Layout(
                                 width='10%',
                                 border='solid'),
                             disabled=True)
                    if 'id' in str(row_item[0]) else
                    ipw.Checkbox(value=row_item[i],
                                 indent=False,
                                 layout=ipw.Layout(
                                     width='10%',
                                     border='0.5px solid'))
                    if isinstance(row_item[i], bool) else
                    ipw.Text(value=str(row_item[i]),
                             layout=ipw.Layout(
                                 width='10%',
                                 border='0.5px solid'),
                             disabled=False)
                    for i in range(0, len(row_item))
                ]) for row_item in existing_table
            ]

            # Selects remaining reagents that are NOT currently in the existing project that user can choose and add
            select_query = f"""
                SELECT reagents.reagent_id, reagent, on_hand
                FROM   reagents
                WHERE  NOT EXISTS (
                   SELECT project_reagents.proj_id, project_reagents.reagent_id
                   FROM   project_reagents
                   WHERE  project_reagents.reagent_id = reagents.reagent_id 
                   AND project_reagents.proj_id = {self.project_choice.value}
                   );     
            """
            # self.cur.execute(select_query)
            # data_table = self.cur.fetchall()
            data_table = self.db.query_call(select_query)
            data_table.insert(0, ['Reagent_id', 'Reagent', 'On Hand'])
            conv_data = []
            for row in data_table[:1]:
                row = list(row) + ['Assay', 'Desired Conc', 'Add']
                conv_data.append(row)
            for row in data_table[1:]:
                row = list(row) + [0, 0, False]
                conv_data.append(row)

            self.add_reagents_container.children = [
                ipw.HBox([
                    ipw.HTML(value=f'<b>{str(row_item[i])}</b>',
                             layout=ipw.Layout(
                                 width='10%',
                                 border='solid'),
                             disabled=True)
                    if 'id' in str(row_item[0]) else
                    ipw.Checkbox(value=row_item[i],
                                 indent=False,
                                 layout=ipw.Layout(
                                     width='10%',
                                     border='0.5px solid'))
                    if isinstance(row_item[i], bool) else
                    ipw.Text(value=str(row_item[i]),
                             layout=ipw.Layout(
                                 width='10%',
                                 border='0.5px solid'),
                             disabled=False)
                    for i in range(0, len(row_item))
                ]) for row_item in conv_data
            ]

        elif self.table_choice.value == 'Project_Standards':
            header = STANDARD_COLS[1:]
            self.output_table_container.children = [
                ipw.Text(
                    description=f"{name}:",
                    style={'description_width': '150px'},
                    layout=ipw.Layout(width='400px')
                ) for name in header
            ]
        else:
            select_query = f"""
            SELECT reagent_id, reagent, assay, on_hand FROM reagents
            """
            # self.cur.execute(select_query)
            # data_table = self.cur.fetchall()
            data_table = self.db.query_call(select_query)
            data_table.insert(0, ['Reagent_id', 'Reagent', 'Assay', 'On Hand'])
            conv_data = []
            for row in data_table[:1]:
                row = list(row) + ['Desired Conc', 'Add']
                conv_data.append(row)
            for row in data_table[1:]:
                row = list(row) + [0, False]
                conv_data.append(row)

            self.add_reagents_container.children = [
                ipw.HBox([
                    ipw.HTML(value=f'<b>{str(row_item[i])}</b>',
                             layout=ipw.Layout(
                                 width='10%',
                                 border='solid'),
                             disabled=True)
                    if 'id' in str(row_item[0]) else
                    ipw.Checkbox(value=row_item[i],
                                 indent=False,
                                 layout=ipw.Layout(
                                     width='10%',
                                     border='0.5px solid'))
                    if isinstance(row_item[i], bool) else
                    ipw.Text(value=str(row_item[i]),
                             layout=ipw.Layout(
                                 width='10%',
                                 border='0.5px solid'),
                             disabled=False)
                    for i in range(0, len(row_item))
                ]) for row_item in conv_data
            ]

    def update_data(self):
        if self.start_menu.value == "View":
            toggle = True
        else:
            toggle = False
        if self.table_choice.value == 'Reagents':
            self.query_header = ', '.join(REAGENT_COLS_QUERY)
            insert_header = ['ID'] + REAGENT_COLS
        elif self.table_choice.value == 'Consumables':
            self.query_header = ', '.join(CONSUMABLE_COLS_QUERY)
            insert_header = ['ID'] + CONSUMABLE_COLS
        elif self.table_choice.value == 'Project_Standards':
            self.query_header = ', '.join(STANDARD_COLS_QUERY)
            insert_header = ['ID'] + STANDARD_COLS
        else:
            self.query_header = ', '.join(PROJECT_COLS_QUERY)
            insert_header = ['ID'] + PROJECT_COLS

        select_query_data = f"""
            SELECT {self.query_header} FROM {self.table_choice.value.lower()}
            """
        # self.cur.execute(select_query_data)
        # data_table = self.cur.fetchall()
        data_table = self.db.query_call(select_query_data)
        data_table.insert(0, insert_header)
        conv_data = []
        for row in data_table[:1]:
            row = list(row) + ['Update'] if self.start_menu.value == 'Update' \
                else list(row) + ['Delete'] if self.start_menu.value == 'Delete' \
                else list(row)
            conv_data.append(row)
        for row in data_table[1:]:
            row = list(row) + [False] if self.start_menu.value in ['Update', 'Delete'] else list(row)
            conv_data.append(row)
        self.output_table_container.children = [
            ipw.HBox([
                ipw.HTML(value=f"<b style='font-size:75%;'>{str(row_item[i])}</b>",
                         layout=ipw.Layout(
                             width='9%',
                             border='solid'),
                         disabled=True)
                if 'ID' in str(row_item[0]) else
                ipw.Checkbox(value=row_item[i],
                             indent=False,
                             layout=ipw.Layout(
                                 width='9%',
                                 border='0.5px solid'))
                if isinstance(row_item[i], bool) else
                ipw.Text(value=str(row_item[i]),
                         layout=ipw.Layout(
                             width='9%',
                             border='0.5px solid'),
                         disabled=toggle)
                for i in range(0, len(row_item))
            ]) for row_item in conv_data
        ]

    def capture_updates(self, event):
        if self.start_menu.value == 'Update':
            self.db.update_table(
                self.output_table_container.children[1:],
                self.table_choice.value,
                self.query_header,
                self.update_message_container
            )
            # row_to_update = []
            # for Hbox in self.output_table_container.children[1:]:
            #     if Hbox.children[-1].value:
            #         update_list = tuple([box.value for box in Hbox.children[:-1]])
            #         row_to_update.append(update_list)
            # with CONN:
            #     cur = CONN.cursor()
            #     for row in row_to_update:
            #         proj_dict = dict(zip(self.query_header.split(','), row))
            #         query_set = [f"{key} = '{value}'" for (key, value) in proj_dict.items()]
            #         set_string = ', '.join(query_set[1:])
            #         update_query = f"""
            #             UPDATE {self.table_choice.value.lower()}
            #             SET {set_string}
            #             WHERE {self.query_header.split(',')[0]} = {row[0]}
            #         """
            #         try:
            #             cur.execute(update_query)
            #         except (Exception, pg2.DatabaseError) as error:
            #             message_split = error.args[0].split('DETAIL:')
            #             self.update_message_container.children = [ipw.HTML('ERROR:')] + [
            #                 ipw.HTML(f'{message}') for message in message_split
            #             ]
            #         else:
            #             CONN.commit()
            #             self.update_message_container.children = [ipw.HTML('<b>Update(s) made!</b>')]

        elif self.start_menu.value == 'Add' and self.table_choice.value in ['Reagents', 'Consumables']:
            self.db.insert_to_cons_reag(
                self.table_choice.value,
                self.query_header,
                self.output_table_container.children,
                self.update_message_container
            )
            # with CONN:
            #     cur = CONN.cursor()
            #     insert_query = f"""
            #     INSERT INTO {self.table_choice.value.lower()} ({', '.join(self.query_header[1:])})
            #     VALUES {str(tuple([box.value for box in self.output_table_container.children]))}
            #     """
            #     try:
            #         cur.execute(insert_query)
            #     except (Exception, pg2.DatabaseError) as error:
            #         message_split = error.args[0].split('DETAIL:')
            #         self.update_message_container.children = [ipw.HTML('ERROR:')] + [
            #             ipw.HTML(f'{message}') for message in message_split
            #         ]
            #     else:
            #         CONN.commit()
            #         self.update_message_container.children = [ipw.HTML(f'{self.table_choice.value} added!</b>')]

        elif self.start_menu.value == 'Add' and self.table_choice.value == 'Project_Standards':
            self.db.insert_to_standards(
                self.table_choice.value,
                self.project_choice.value,
                self.output_table_container.children,
                self.update_message_container
            )
            # with CONN:
            #     insert_values = [box.value for box in self.output_table_container.children]
            #     insert_values.insert(0, self.project_choice.value)
            #     cur = CONN.cursor()
            #     insert_query = f"""
            #         INSERT INTO {self.table_choice.value.lower()} ({', '.join(STANDARD_COLS_QUERY[1:])})
            #         VALUES {str(tuple(insert_values))}
            #     """
            #     try:
            #         cur.execute(insert_query)
            #     except (Exception, pg2.DatabaseError) as error:
            #         message_split = error.args[0].split('DETAIL:')
            #         self.update_message_container.children = [ipw.HTML('ERROR:')] + [
            #             ipw.HTML(f'{message}') for message in message_split
            #         ]
            #     else:
            #         CONN.commit()
            #         self.update_message_container.children = [ipw.HTML(f'Project standard added!</b>')]

        elif self.start_menu.value == 'Add' and self.table_choice.value == 'Projects':
            self.db.add_insert_to_projects(
                self.proj_type.value,
                self.table_choice.value,
                self.project_choice.value,
                self.output_table_container,
                self.add_reagents_container.children[1:],
                self.update_message_container
            )
            # with CONN:
            #     cur = CONN.cursor()
            #     if self.proj_type.value == 'New':
            #         proj_name = self.output_table_container.children[0].value
            #         insert_query = f"""
            #             INSERT INTO projects (proj_name)
            #             VALUES ('{proj_name}')
            #             RETURNING proj_id
            #         """
            #         try:
            #             cur.execute(insert_query)
            #         except (Exception, pg2.DatabaseError) as error:
            #             message_split = error.args[0].split('DETAIL:')
            #             self.update_message_container.children = [ipw.HTML('ERROR:')] + [
            #                 ipw.HTML(f'{message}') for message in message_split
            #             ]
            #             proj_id = None
            #         else:
            #             proj_id = cur.fetchone()[0]
            #             CONN.commit()
            #
            #         select_query = f"""
            #             SELECT proj_id FROM projects
            #             WHERE proj_name = '{proj_name}'
            #         """
            #         cur.execute(select_query)
            #         proj_id = cur.fetchall()[0][0]
            #     else:
            #         proj_id = self.project_choice.value
            #     if not proj_id:
            #         pass
            #     else:
            #         row_to_add = []
            #         for Hbox in self.add_reagents_container.children[1:]:
            #             if Hbox.children[-1].value:
            #                 add_list = tuple(
            #                     [proj_id] +
            #                     [Hbox.children[0].value] +
            #                     [box.value for box in Hbox.children[-3:-1]]
            #                 )
            #                 row_to_add.append(add_list)
            #
            #         for row in row_to_add:
            #             insert_query = f"""
            #                 INSERT INTO project_reagents (proj_id, reagent_id, assay_id, desired_conc)
            #                 VALUES {str(row)}
            #             """
            #             try:
            #                 cur.execute(insert_query)
            #             except (Exception, pg2.DatabaseError) as error:
            #                 message_split = error.args[0].split('DETAIL:')
            #                 self.update_message_container.children = [ipw.HTML('ERROR:')] + [
            #                     ipw.HTML(f'{message}') for message in message_split
            #                 ]
            #             else:
            #                 CONN.commit()
            #                 self.update_message_container.children = [ipw.HTML(f'{self.table_choice.value} added/updated!</b>')]

        elif self.start_menu.value == 'Delete':
            self.db.delete_data(
                self.table_choice.value,
                self.output_table_container.children[1:],
                self.update_message_container
            )
            # with CONN:
            #     cur = CONN.cursor()
            #     pk_id = PROJECT_COLS_QUERY[0] if self.table_choice.value == 'Projects' else REAGENT_COLS_QUERY[0] \
            #         if self.table_choice.value == 'Reagents' else CONSUMABLE_COLS_QUERY[0] \
            #         if self.table_choice.value == 'Consumables' else STANDARD_COLS_QUERY[0] \
            #         if self.table_choice.value == 'Project_Standards' else ""
            #
            #     row_to_delete = []
            #     for Hbox in self.output_table_container.children[1:]:
            #         if Hbox.children[-1].value:
            #             delete_list = tuple([box.value for box in Hbox.children[:-1]])
            #             row_to_delete.append(delete_list)
            #     for row in row_to_delete:
            #         insert_query = f"""
            #             DELETE FROM {self.table_choice.value}
            #             WHERE {pk_id} = {row[0]}
            #         """
            #         try:
            #             cur.execute(insert_query)
            #         except (Exception, pg2.DatabaseError) as error:
            #             message_split = error.args[0].split('DETAIL:')
            #             self.update_message_container.children = [ipw.HTML('ERROR:')] + [
            #                 ipw.HTML(f'{message}') for message in message_split
            #             ]
            #         else:
            #             CONN.commit()
            #             self.update_message_container.children = [ipw.HTML(f'Sorry! Still under construction ¯\_(ツ)_/¯ </b>')]


if __name__ == "__main__":
    db_control = DbControl()
