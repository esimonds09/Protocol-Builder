import psycopg2 as pg2
import ipywidgets as ipw
from IPython.display import display
from config import config, Headers
# from db_control.db_main import Db


class Db:
    def __init__(self, params):
        self.params = params
        self.__connect()
        self.headers = Headers()

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

    def update_table(self, data, table, query_header):
        row_to_update = []
        # return_value = []
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
                    RETURNING {query_header.split(',')[-1]}
                """
                try:
                    cur.execute(update_query)
                except (Exception, pg2.DatabaseError) as error:
                    message_split = error.args[0].split('DETAIL:')
                    message_container = [ipw.HTML('ERROR:')] + [
                        ipw.HTML(f'{msg}') for msg in message_split
                    ]
                else:
                    update_count += cur.rowcount
                    return_data = cur.fetchone()[-1]

                    message_container = [ipw.HTML(f'<b>Update(s) made! {update_count} row(s) updated. Value updated: {return_data}</b>')]
                    # return_value.append(cur.fetchone()[0])

                    self.conn.commit()
        return message_container

    def insert_to_cons_reag(self, table, query_header, data):
        with self.conn:
            cur = self.conn.cursor()
            insert_query = f"""
            INSERT INTO {table.lower()} ({', '.join(query_header[1:])})
            VALUES {str(tuple([box.value for box in data]))}
            RETURNING {query_header[0]}, on_hand
            """
            try:
                cur.execute(insert_query)
            except (Exception, pg2.DatabaseError) as error:
                message_split = error.args[0].split('DETAIL:')
                message_container = [ipw.HTML('ERROR:')] + [
                    ipw.HTML(f'{message}') for message in message_split
                ]
                returned_id = ""
            else:
                returned_data = cur.fetchone()
                returned_id = returned_data[0]
                returned_on_hand = returned_data[1]
                self.conn.commit()
                message_container = [ipw.HTML(f'<b>{table} added! On Hand: {returned_on_hand}</b>')]

        return message_container, returned_id

    def insert_to_standards(self, table, project, data):
        with self.conn:
            insert_values = [box.value for box in data]
            insert_values.insert(0, project)
            cur = self.conn.cursor()
            insert_query = f"""
                INSERT INTO {table.lower()} ({', '.join(self.headers.standard_query_cols[1:])})
                VALUES {str(tuple(insert_values))}
                RETURNING standard_id, on_hand
            """
            try:
                cur.execute(insert_query)
            except (Exception, pg2.DatabaseError) as error:
                message_split = error.args[0].split('DETAIL:')
                message_container = [ipw.HTML('ERROR:')] + [
                    ipw.HTML(f'{message}') for message in message_split
                ]
                returned_id = ""
            else:
                returned_data = cur.fetchone()
                returned_id = returned_data[0]
                returned_on_hand = returned_data[1]
                self.conn.commit()
                message_container = [ipw.HTML(f'<b>Project standard added! On hand: {returned_on_hand}</b>')]
        return message_container, returned_id

    def add_insert_to_projects(self, proj_type, table, project, new_proj, reagent_data):
        with self.conn:
            cur = self.conn.cursor()
            if proj_type == 'New':
                proj_name = new_proj[0].value
                insert_query = f"""
                    INSERT INTO projects (proj_name)
                    VALUES ('{proj_name}')
                    RETURNING proj_id
                """
                try:
                    cur.execute(insert_query)
                except (Exception, pg2.DatabaseError) as error:
                    message_split = error.args[0].split('DETAIL:')
                    message_container = [ipw.HTML('ERROR:')] + [
                        ipw.HTML(f'{message}') for message in message_split
                    ]
                    proj_id = None
                else:
                    proj_id = cur.fetchone()[0]
                    self.conn.commit()
            else:
                proj_id = project
            if not proj_id:
                message_container = [ipw.HTML("No project entered.")]
                returned_id = ""
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
                        RETURNING reagent_id
                    """
                    try:
                        cur.execute(insert_query)
                    except (Exception, pg2.DatabaseError) as error:
                        message_split = error.args[0].split('DETAIL:')
                        message_container = [ipw.HTML('ERROR:')] + [
                            ipw.HTML(f'{message}') for message in message_split
                        ]
                        returned_id = ""
                    else:
                        returned_id = cur.fetchone()[0]
                        self.conn.commit()
                        message_container = [ipw.HTML(f'{table} added/updated!</b>')]
        return message_container, proj_id, returned_id

    def delete_data(self, table, data):
        with self.conn:
            cur = self.conn.cursor()
            pk_id = self.headers.project_query_cols[0] if table == 'Projects' else self.headers.reagent_query_cols[0] \
                if table == 'Reagents' else self.headers.consumable_query_cols[0] \
                if table == 'Consumables' else self.headers.standard_query_cols[0] \
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
                    message_container = [ipw.HTML('ERROR:')] + [
                        ipw.HTML(f'{message}') for message in message_split
                    ]
                else:
                    self.conn.commit()
                    message_container = [
                        ipw.HTML(f'Sorry! Still under construction ¯\_(ツ)_/¯ </b>')]
        return message_container

    def query_call(self, query):
        with self.conn:
            cur = self.conn.cursor()
            cur.execute(query)
            if 'SELECT' in query:
                data = cur.fetchall()
                return data


class InputForm:
    """
    This class is responsible for the front-end inventory tracking form (inventory_form.ipynb).
    Using the pyscopg2 package, queries are run to update, add to, and show inventory.

    """
    def __init__(self):
        self.headers = Headers()
        # self.cur = CONN.cursor()
        try:
            self.params = config()
        except Exception:
            self.params = config(filename='../database.ini', section='postgresql')
        finally:
            self.db = Db(self.params)

        self.start_menu = ipw.Dropdown(
            description='Choose option:',
            options=self.headers.start_list,
            value=self.headers.start_list[0],
            style=self.headers.style
        )
        # Table choices
        self.table_choice = ipw.Dropdown(
            description='Choose table:',
            options=self.headers.table_choice,
            value=self.headers.table_choice[0],
            style=self.headers.style
        )

        # New or Existing project to add to
        self.proj_type = ipw.Dropdown(
            description='Add to:',
            options=['...', 'New', 'Existing'],
            value='...',
            style=self.headers.style,
            disabled=True
        )

        # Project choices
        self.proj_names = self.db.choose_project()
        self.project_choice = ipw.Dropdown(
            description='Choose project:',
            options=self.proj_names,
            value=self.proj_names['...'],
            style=self.headers.style,
            disabled=True
        )

        self.capture_inputs_button = ipw.Button(
            description='Enter Inputs',
            button_style='info',
            style=self.headers.style
        )
        self.capture_inputs_button.on_click(self.capture_inputs)

        self.out_display = ipw.Output()

        self.initialize_input_section()

    def initialize_input_section(self):
        """
        INPUT SECTION
        """
        input_wdgt_container = ipw.VBox()

        input_section_container = ipw.VBox([
            ipw.HTML("<h2>Inventory Tracker</h2>"),
            ipw.HTML("<hr style='background-color:black;'>"),
            ipw.HTML("<h3>Input Section</h3>"),
            ipw.HTML("<hr style='background-color:black;'>"),
            input_wdgt_container,
            ipw.HTML('<br>'),
            # self.capture_inputs_button,
            self.out_display
        ])
        input_wdgt_container.children = [
            ipw.HBox([
                self.start_menu,
                self.table_choice,
                ipw.VBox([
                    self.proj_type,
                    self.project_choice
                ])
            ]),
            self.capture_inputs_button
        ]

        def enable_dropdowns(option, table, p_type, project):
            if option == 'Add' and table in ["Projects", "Project_Standards"]:
                if table == "Projects" and p_type == "...":
                    self.proj_type.disabled = False
                    self.project_choice.value = self.proj_names['...']
                    self.project_choice.disabled = True
                elif table == "Projects" and p_type == "Existing":
                    self.proj_names = self.db.choose_project()
                    self.project_choice.options = self.proj_names
                    self.project_choice.disabled = False
                elif table == "Project_Standards":
                    self.proj_type.value = '...'
                    self.proj_type.disabled = True
                    self.project_choice.disabled = False
            elif option == 'Add' and table not in ["Projects", "Projects_Standards"]:
                self.proj_type.value = '...'
                self.proj_type.disabled = True
                self.project_choice.value = self.proj_names['...']
                self.project_choice.disabled = True
            else:
                self.proj_type.value = '...'
                self.proj_type.disabled = True
                self.project_choice.value = self.proj_names['...']
                self.project_choice.disabled = True

        ipw.interactive(enable_dropdowns,
                        option=self.start_menu,
                        table=self.table_choice,
                        p_type=self.proj_type,
                        project=self.project_choice)

        display(input_section_container)

    def capture_inputs(self, event):
        pass_checks = False
        if '...' in [self.start_menu.value, self.table_choice.value]:
            message = ipw.HTML('Please choose both a start option and table choice!')
        elif self.table_choice.value in ["Projects", "Project_Standards"] and self.start_menu.value == "Add":
            if self.table_choice.value == "Projects" and self.proj_type.value == '...':
                message = ipw.HTML('Please choose new or existing!')
            elif self.project_choice.label == '...' and self.proj_type.value != 'New':
                message = ipw.HTML('Please choose a project!')
            else:
                message = ipw.HTML('Inputs selected!')
                pass_checks = True

            with self.out_display:
                self.out_display.clear_output()
                display(message)
        else:
            message = ipw.HTML('Inputs selected!')
            pass_checks = True

        with self.out_display:
            self.out_display.clear_output()
            display(message)

        if pass_checks:
            input_choices = dict(
                option=self.start_menu.value,
                table=self.table_choice.value,
                p_type=self.proj_type.value,
                project=self.project_choice.value
            )
            with self.out_display:
                self.out_display.clear_output()
                Processor(**input_choices)


class Processor:
    def __init__(self, option, table, p_type, project):
        self.headers = Headers()
        try:
            self.params = config()
        except Exception:
            self.params = config(filename='../database.ini', section='postgresql')
        finally:
            self.db = Db(self.params)

        self.option = option
        self.table = table
        self.p_type = p_type
        self.project = project
        self.table_output = ipw.Output()

        self.proj_name = []
        self.current_reagents = []
        self.add_reagents = []
        self.data_table = []
        self.query_header = None
        self.message_container = []

        self.updates_button = ipw.Button(
            description='Update',
            button_style='info',
            style=self.headers.style
        )
        self.updates_button.on_click(self.capture_updates)

        # display(ipw.HTML(f'Ok good {self.option} {self.table} {self.p_type} {self.project}'))
        self.display_data()

    def display_data(self):
        if self.option == 'Add':
            if self.table == "Projects" and self.p_type == 'New':
                self.proj_name, self.add_reagents = self.new_proj_name()
            elif self.table == "Projects" and self.p_type == 'Existing':
                self.current_reagents, self.add_reagents = self.add_data_to_proj()
            else:
                self.data_table = self.add_data()
        elif self.option in ['View', 'Update']:
            self.query_header, insert_header = self.get_query_header()
            self.data_table = self.update_data(insert_header)

        output_section_container = ipw.VBox([
            ipw.HTML("<h3>Output Section</h3>"),
            ipw.HTML("<hr style='background-color:black;'>"),
            ipw.VBox(self.proj_name),
            ipw.VBox(self.current_reagents),
            ipw.VBox(self.add_reagents),
            ipw.VBox(self.data_table),

            # add_reagents_container,
            ipw.HTML('<br>'),
            ipw.HBox([
                self.updates_button
            ]),
            ipw.VBox(self.message_container)
        ])

        display(output_section_container)

    def add_data(self):
        """
        This function will insert new data into reagents and consumables
        This function requires column headers
        """
        # Input boxes to capture add data will show in output table
        if self.table == 'Reagents':
            header = self.headers.reagent_cols
            self.query_header = self.headers.reagent_query_cols
        elif self.table == 'Consumables':
            header = self.headers.consumable_cols
            self.query_header = self.headers.consumable_query_cols
        elif self.table == 'Project_Standards':
            header = self.headers.standard_cols[1:]
            self.query_header = self.headers.standard_query_cols
        else:
            header = ""

        output_table_container = [
            ipw.Text(
                description=f"{name}:",
                style={'description_width': '150px'},
                layout=ipw.Layout(width='400px')
            ) for name in header
        ]
        return output_table_container

    def new_proj_name(self):
        display(ipw.HTML('Call worked'))
        proj_name_container = [
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
        data_table.insert(0, ['Reagent_id', 'Reagent', 'On Hand'])
        conv_data = []
        for row in data_table[:1]:
            row = list(row) + ['Assay', 'Desired Conc', 'Add']
            conv_data.append(row)
        for row in data_table[1:]:
            row = list(row) + [0, 0, False]
            conv_data.append(row)

        reagents_container = [
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
        return proj_name_container, reagents_container

    def add_data_to_proj(self):
        # Addition of reagents to an existing project
        # Selects current reagents from the existing project
        select_query = f"""
        SELECT reagents.reagent_id, reagent, on_hand, project_reagents.assay_id, project_reagents.desired_conc 
        FROM reagents
        INNER JOIN project_reagents
        ON project_reagents.reagent_id = reagents.reagent_id
        WHERE project_reagents.proj_id = {self.project}            
        """
        existing_table = self.db.query_call(select_query)

        existing_table.insert(0, ['Reagent_id', 'Reagent', 'On Hand', 'Assay', 'Desired Conc'])
        current_reagents_container = [
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
               AND project_reagents.proj_id = {self.project}
               );     
        """
        data_table = self.db.query_call(select_query)
        data_table.insert(0, ['Reagent_id', 'Reagent', 'On Hand'])
        conv_data = []
        for row in data_table[:1]:
            row = list(row) + ['Assay', 'Desired Conc', 'Add']
            conv_data.append(row)
        for row in data_table[1:]:
            row = list(row) + [0, 0, False]
            conv_data.append(row)

        add_reagents_container = [
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
        return current_reagents_container, add_reagents_container

    def update_data(self, insert_header):
        if self.option == 'View':
            toggle = True
        else:
            toggle = False

        select_query_data = f"""
            SELECT {self.query_header} FROM {self.table.lower()}
            """

        data_table = self.db.query_call(select_query_data)
        data_table.insert(0, insert_header)
        conv_data = []
        for row in data_table[:1]:
            row = list(row) + ['Update'] if self.option == 'Update' \
                else list(row) + ['Delete'] if self.option == 'Delete' \
                else list(row)
            conv_data.append(row)
        for row in data_table[1:]:
            row = list(row) + [False] if self.option in ['Update', 'Delete'] else list(row)
            conv_data.append(row)
        output_table_container = [
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
        return output_table_container

    def get_query_header(self):
        if self.table == 'Reagents':
            query_header = ', '.join(self.headers.reagent_query_cols)
            insert_header = ['ID'] + self.headers.reagent_cols
        elif self.table == 'Consumables':
            query_header = ', '.join(self.headers.consumable_query_cols)
            insert_header = ['ID'] + self.headers.consumable_cols
        elif self.table == 'Project_Standards':
            query_header = ', '.join(self.headers.standard_query_cols)
            insert_header = ['ID'] + self.headers.standard_cols
        else:
            query_header = ', '.join(self.headers.project_query_cols)
            insert_header = ['ID'] + self.headers.project_cols

        return query_header, insert_header

    def capture_updates(self, event):
        # display(ipw.HTML(f'{self.option}-{self.table}-{self.p_type}-{self.project}-{self.query_header}'))
        if self.option == 'Update':
            message_container = self.db.update_table(
                self.data_table[1:],
                self.table,
                self.query_header
            )
            display(ipw.VBox(message_container))

        elif self.option == 'Add' and self.table in ['Reagents', 'Consumables']:
            message_container = self.db.insert_to_cons_reag(
                self.table,
                self.query_header,
                self.data_table,
            )
            display(ipw.VBox(message_container))
        elif self.option == 'Add' and self.table == 'Project_Standards':
            message_container = self.db.insert_to_standards(
                self.table,
                self.project,
                self.data_table,
            )

        elif self.option == 'Add' and self.table == 'Projects':
            message_container = self.db.add_insert_to_projects(
                self.p_type,
                self.table,
                self.project,
                self.proj_name,
                self.add_reagents[1:]
            )

        elif self.option == 'Delete':
            message_container = self.db.delete_data(
                self.table,
                self.data_table[1:],
            )


if __name__ == "__main__":
    db_control = InputForm()


    # def add_project_standards(self):

        # else:
        #     select_query = f"""
        #     SELECT reagent_id, reagent, assay, on_hand FROM reagents
        #     """
        #     # self.cur.execute(select_query)
        #     # data_table = self.cur.fetchall()
        #     data_table = self.db.query_call(select_query)
        #     data_table.insert(0, ['Reagent_id', 'Reagent', 'Assay', 'On Hand'])
        #     conv_data = []
        #     for row in data_table[:1]:
        #         row = list(row) + ['Desired Conc', 'Add']
        #         conv_data.append(row)
        #     for row in data_table[1:]:
        #         row = list(row) + [0, False]
        #         conv_data.append(row)
        #
        #     self.add_reagents_container.children = [
        #         ipw.HBox([
        #             ipw.HTML(value=f'<b>{str(row_item[i])}</b>',
        #                      layout=ipw.Layout(
        #                          width='10%',
        #                          border='solid'),
        #                      disabled=True)
        #             if 'id' in str(row_item[0]) else
        #             ipw.Checkbox(value=row_item[i],
        #                          indent=False,
        #                          layout=ipw.Layout(
        #                              width='10%',
        #                              border='0.5px solid'))
        #             if isinstance(row_item[i], bool) else
        #             ipw.Text(value=str(row_item[i]),
        #                      layout=ipw.Layout(
        #                          width='10%',
        #                          border='0.5px solid'),
        #                      disabled=False)
        #             for i in range(0, len(row_item))
        #         ]) for row_item in conv_data
        #     ]
    # def reset(self, event):
    #     """
    #     This function will reset all the boxes and placeholders, as well as re-enable disabled input boxes
    #     """
    #     self.initialize_input_section()
    #     # self.out_display.clear_output()
    #     # self.start_menu.value = '...'
    #     # self.start_menu.disabled = False
    #     # self.table_choice.value = '...'
    #     # self.table_choice.disabled = False
    #     # self.proj_type.value = '...'
    #     # self.proj_type.disabled = False
    #     # self.project_choice.disabled = False
    #     # self.first_placeholder.children = []
    #     # self.second_placeholder.children = []
    #     # self.output_table_container.children = []
    #     # self.current_reagents_container.children = []
    #     # self.add_reagents_container.children = []
    #     # self.update_message_container.children = []