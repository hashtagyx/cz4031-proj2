from explore import execute_query, is_query_valid, connect_to_database
import numpy as np
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QMessageBox, QScrollArea, QLabel, QComboBox, QTextBrowser, QTableWidget, QTableWidgetItem, QHeaderView
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from math import floor
import ast
import json
import textwrap  

class App(QMainWindow):
    def __init__(self, connection_params):
        super().__init__()
        self.connection_params = connection_params
        try:
            self.db_connection = connect_to_database(connection_params)
            print("Connected to the database successfully")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {e}")
        self.title = 'SQL Query Visualizer'
        self.data = None
        self.current_lat = None
        self.current_lon = None
        self.table_to_colour_grids = {}
        self.last_clicked_cell = None
        self.selected_relation = None  # Initialize to None
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.resize(800, 400)
        self.move(100, 100)
        
        # Create a central widget
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")

        # Create a QVBoxLayout
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout.setObjectName("verticalLayout")

        # Add label to the layout
        self.label = QtWidgets.QLabel("Enter SQL Query Here:")
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)

        # Add plain text edit to the layout
        self.plainTextEdit = QtWidgets.QPlainTextEdit()
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.plainTextEdit.setMaximumHeight(100)
        self.verticalLayout.addWidget(self.plainTextEdit)

        # Add execute button to the layout
        self.exeButton = QtWidgets.QPushButton("Execute Query")
        self.exeButton.setObjectName("exeButton")
        self.verticalLayout.addWidget(self.exeButton)

        # Add horizontal layout for other buttons
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        # Add QEP button to the horizontal layout
        self.qepButton = QtWidgets.QPushButton("View Query Execution Plan")
        self.qepButton.setObjectName("qepButton")
        self.horizontalLayout.addWidget(self.qepButton)

        # Add Visualize button to the horizontal layout
        self.visButton = QtWidgets.QPushButton("Visualize Blocks")
        self.visButton.setObjectName("visButton")
        self.horizontalLayout.addWidget(self.visButton)

        # Add horizontal layout to the main vertical layout
        self.verticalLayout.addLayout(self.horizontalLayout)

        # spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        # self.verticalLayout.addItem(spacerItem)

        self.num_blocks_explored = QLabel("Blocks Explored:")
        self.select_relation = QLabel("Select Relation:")
        self.select_block_id = QLabel("Select Block ID:")
        # view tuples in selected block
        self.block_tuple_viewer = QTextBrowser()

        # dropdowns selection
        self.relation_selector = QComboBox()
        self.relation_selector.setEnabled(False)
        self.relation_selector.currentTextChanged.connect(lambda relation: self.update_relation_selector(relation))

        self.block_id_selector = QComboBox()
        self.block_id_selector.setEnabled(False)
        self.block_id_selector.currentTextChanged.connect(lambda block_id: self.display_curr_block_contents(block_id))

        # Initialize table and scroll area as instance variables
        self.table = None
        self.scroll_area = None

        self.verticalLayout.addWidget(self.num_blocks_explored)
        self.verticalLayout.addWidget(self.select_relation)
        self.verticalLayout.addWidget(self.relation_selector)
        self.verticalLayout.addWidget(self.select_block_id)
        self.verticalLayout.addWidget(self.block_id_selector)
        # self.verticalLayout.addWidget(self.block_tuple_viewer)

        # Connecting buttons to their functions
        self.exeButton.clicked.connect(self.on_submit)
        self.visButton.clicked.connect(self.display_plot)

        # Set the central widget
        self.setCentralWidget(self.centralwidget)

        self.show()

    def on_submit(self):
        # Execute the SQL query here (placeholder function)
        query = self.plainTextEdit.toPlainText()
        print(f"Executing SQL Query: {query}")
        
        if is_query_valid(query):
            data = execute_query(query, self.connection_params)
            if not data['explain_result']:
                print('Invalid query')
                QMessageBox.warning(self, "Error", "Invalid query.")
                self.data = None
                return
            # Display the Matplotlib plot
            # self.display_plot(data)
            self.data = data
            relations = list(data['block_dict'].keys())
            self.relation_selector.clear()
            self.relation_selector.addItems(relations)
            self.relation_selector.setEnabled(True)
        else:
            self.data = None
            if len(query) == 0:
                QMessageBox.warning(self, "Error", "No input found. Please enter an SQL SELECT query.")
                print('No input found.')
            else:
                QMessageBox.warning(self, "Error", "Forbidden keyword in query. (DELETE, UPDATE, WITH)")
                print('Forbidden keyword in query.')

    def update_relation_selector(self, relation):
        self.selected_relation = relation
        if self.selected_relation == '':
            return
        block_ids = self.data['block_dict'][relation]

        last_block = ast.literal_eval(self.data['block_result'][relation][-1][-1][f"{relation}_ctid"])[0]
        first_block = ast.literal_eval(self.data['block_result'][relation][0][0][f"{relation}_ctid"])[0]
        # last_block_index = block_ids.index(last_block)
        # block_ids = self.data['block_dict'][relation][:last_block_index+1]
        block_ids = [x for x in range(first_block, last_block+1)]

        block_ids = list(map(str, block_ids))
        self.block_id_selector.clear()
        self.block_id_selector.addItems(block_ids)
        self.block_id_selector.setEnabled(True)
        # Update the label with the number of blocks hit
        blocks_hit = len(self.data['block_dict'][relation])
        self.num_blocks_explored.setText(f"Blocks Explored: {blocks_hit}")


    def display_curr_block_contents(self, block_id):
        if self.selected_relation is not None and block_id != '':
            smallest_index = self.data['block_dict'][self.selected_relation][0]
            index = int(block_id) - smallest_index
            block_content = self.data['block_result'][self.selected_relation][index]

            # Clear existing content in the QTextBrowser
            self.block_tuple_viewer.clear()

            # Display the content in a table
            self.display_table(block_content)

    def display_table(self, block_content):
        if not block_content:
            return

        # Clear existing table and scroll area
        if self.table is not None:
            self.table.setParent(None)
        if self.scroll_area is not None:
            self.scroll_area.setParent(None)

        # Create a table widget
        self.table = QTableWidget()

        # Set the number of rows and columns
        self.table.setRowCount(len(block_content))
        self.table.setColumnCount(len(block_content[0]))

        # Set the table headers
        headers = list(block_content[0].keys())
        self.table.setHorizontalHeaderLabels(headers)

        # Populate the table with data
        for row, entry in enumerate(block_content):
            for col, key in enumerate(headers):
                item = QTableWidgetItem(str(entry[key]))
                self.table.setItem(row, col, item)

        # Auto-resize columns to contents
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # Create a scroll area and set the table as its widget
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.table)
        self.scroll_area.setWidgetResizable(True)

        # Clear the existing content of QTextBrowser (if any)
        self.block_tuple_viewer.clear()

        # Add the scroll area directly to the layout
        self.verticalLayout.addWidget(self.scroll_area)
        self.resize(max(self.width(), 800), max(self.height(), 800))
        # # Add the scroll area to the QTextBrowser
        # self.block_tuple_viewer.setLayout(QVBoxLayout())
        # self.block_tuple_viewer.layout().addWidget(self.scroll_area)

    def display_plot(self):
        # Matplotlib plot
        matplotlib.pyplot.close('all')
        if not self.data:
            QMessageBox.warning(self, "Error", "Please execute a query first.")
            return
        fig, axs = self.create_matplotlib_plot(self.data)

        # Opens a new window with the visualization of the first 100 blocks from the first block hit
        fig.show()

    def create_matplotlib_plot(self, data):
        self.last_clicked_cell = None
        self.table_to_colour_grids = {}
        block_result = data['block_result']
        num_tables = len(block_result)
        tables = list(block_result.keys())

        fig, axs = plt.subplots(num_tables, 2, figsize=(8, 2 * num_tables), gridspec_kw={'hspace': 0.5})
        
        lon_range = np.arange(0, 10, 1)
        lat_range = np.arange(0, 10, 1)

        def make_on_move_lambda(ax, table_name, grid_colour, m):
            return lambda event: on_move(event, ax, table_name, grid_colour, m)

        def on_move(event, ax, table_name, grid_colour, m):
            if event.inaxes is ax:
                event_lat = event.ydata if -0.5 <= event.ydata < len(lat_range) else None
                event_lon = event.xdata if -0.5 <= event.xdata < len(lon_range) else None

                # Only update if we have valid coordinates and they are different than the previous update
                if event_lat is not None and event_lon is not None and (event_lat != self.current_lat or event_lon != self.current_lon):
                    self.current_lat = round(event_lat)
                    self.current_lon = round(event_lon)
                    block_number = self.current_lat*10 + self.current_lon
                    if block_number < len(block_result[table_name]):
                        block_data = block_result[table_name][self.current_lat*10 + self.current_lon]
                        # Wrap the text using textwrap
                        # wrapped_text = textwrap.fill(f"{self.current_lat} Long, {self.current_lon} Lat, Event Long: {event_lon}, Event Lat: {event_lat}, {table_name} Table, {block_data[0][f'{table_name}_ctid']}", width=20)
                        # block number, no of tuples, no of tuples hit
                        # print(block_data)
                        block_number = ast.literal_eval(block_data[0][f"{table_name}_ctid"])[0]
                        no_of_tuples = len(block_data)
                        count_true = sum(1 for entry in block_data if entry.get("fetched"))

                        wrapped_text = f"Table Name: {table_name}\nCurrent Block: {block_number}\nNumber of Tuples in Block: {no_of_tuples}\nNumber of Tuples Hit: {count_true}"
                        wrapped_text = '\n'.join(wrapped_text.split('\n'))
                        

                        # # remove json appending 
                        # file_path = 'hover_output.json' # Replace with your file path
                        # with open(file_path, 'w') as file:
                        #     json.dump(block_data, file)
                    else:
                        # block_data = f'EMPTY BLOCK {block_number} \n{self.current_lat} Long, {self.current_lon} Lat \n Event Long: {event_lon}, Event Lat: {event_lat}'
                        wrapped_text = f'Table Name: {table_name}\nCurrent Block: {block_number}\nEmpty Block'
                        wrapped_text = '\n'.join(wrapped_text.split('\n'))
                        
                        
                        # wrapped_text = textwrap.fill(block_data, width=20)
                    if num_tables > 1:
                        axs[-1, 1].clear()
                        axs[-1, 1].text(0.5, 0.5, wrapped_text, ha='center', va='center', fontsize=12)
                        axs[-1, 1].axis('off')
                    else:
                        axs[1].clear()
                        axs[1].text(0.5, 0.5, wrapped_text, ha='center', va='center', fontsize=12)
                        axs[1].axis('off')
                    fig.canvas.draw_idle()

                x_index = int(event.xdata + 0.5)
                y_index = int(event.ydata + 0.5)
                
                if 0 <= x_index < grid_colour.shape[1] and 0 <= y_index < grid_colour.shape[0]:
                    # Restore the color of last click
                    if self.last_clicked_cell:
                        old_table, old_y, old_x, old_colour = self.last_clicked_cell
                        old_m, old_grid_colour = self.table_to_colour_grids[old_table]
                        old_grid_colour[old_y, old_x] = old_colour
                        old_m.set_array(old_grid_colour.ravel())
                    # Change the color of the clicked cell
                    self.last_clicked_cell = (table_name, y_index, x_index, grid_colour[y_index, x_index])
                    grid_colour[y_index, x_index] = 0.5

                    # Update the color mesh with the new color
                    m.set_array(grid_colour.ravel())

                    # Redraw the canvas
                    fig.canvas.draw_idle()

        for i in range(num_tables):
            if num_tables > 1:
                ax = axs[i, 0]  # Use two indices if axs is 2D
                axs[i, 1].clear()
                axs[i, 1].axis('off')
            else:
                ax = axs[0]  # Use one index if axs is 1D
                axs[1].clear()
                axs[1].axis('off')

            table = tables[i]
            blocks = block_result[table]
            blocks_accessed = data['block_dict'][table]
            blocks_accessed_set = set(blocks_accessed)

            ctid_name = table + '_ctid'
            starting_block = ast.literal_eval(blocks[0][0][ctid_name])[0]

            grid_colour = np.zeros((10, 10))
            for block in range(starting_block, starting_block + 100):
                if block in blocks_accessed_set:
                    block_offset = block - starting_block
                    row = block_offset//10
                    col = block_offset%10
                    grid_colour[row][col] = 1

            mlon, mlat = np.meshgrid(lon_range, lat_range)

            # plot colour mesh, add edgecolors and linewidths to draw borders around cells
            m = ax.pcolormesh(mlon, mlat, grid_colour, cmap='Blues', edgecolors='black', linewidths=0.5, vmin=0, vmax=1)
            self.table_to_colour_grids[table] = (m, grid_colour)

            ax.set_title(f'Table Name: {table}')
            
            # Connect the same on_move listener to all graphs
            on_move_lambda = make_on_move_lambda(ax, table, grid_colour, m)
            cid = fig.canvas.mpl_connect('button_press_event', on_move_lambda)

        return fig, ax
    
    