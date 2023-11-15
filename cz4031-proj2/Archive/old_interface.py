from explore import execute_query, is_query_valid, connect_to_database
import numpy as np
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QMessageBox, QScrollArea, QLabel
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
        self.left = 100
        self.top = 100
        self.width = 800
        self.height = 600
        self.json_output = None
        self.current_lat = None
        self.current_lon = None
        self.table_to_colour_grids = {}
        self.last_clicked_cell = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.resize(800, 600)
        
        # Create a central widget
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")

        # Create a vertical layout widget
        self.verticalLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(0, 0, 800, 600))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")

        # Create a QVBoxLayout
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout.setObjectName("verticalLayout")

        # Add label to the layout
        self.label = QtWidgets.QLabel("Enter SQL Query Here:", self.verticalLayoutWidget)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)

        # Add plain text edit to the layout
        self.plainTextEdit = QtWidgets.QPlainTextEdit(self.verticalLayoutWidget)
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.verticalLayout.addWidget(self.plainTextEdit)

        # Add execute button to the layout
        self.exeButton = QtWidgets.QPushButton("Execute Query", self.verticalLayoutWidget)
        self.exeButton.setObjectName("exeButton")
        self.verticalLayout.addWidget(self.exeButton)

        # Add horizontal layout for other buttons
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        # Add QEP button to the horizontal layout
        self.qepButton = QtWidgets.QPushButton("View Query Execution Plan", self.verticalLayoutWidget)
        self.qepButton.setObjectName("qepButton")
        self.horizontalLayout.addWidget(self.qepButton)

        # Add Visualize button to the horizontal layout
        self.visButton = QtWidgets.QPushButton("Visualize Blocks", self.verticalLayoutWidget)
        self.visButton.setObjectName("visButton")
        self.horizontalLayout.addWidget(self.visButton)

        # Add horizontal layout to the main vertical layout
        self.verticalLayout.addLayout(self.horizontalLayout)

        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)

        # Set the central widget
        self.setCentralWidget(self.centralwidget)

        # Connecting buttons to their functions
        self.exeButton.clicked.connect(self.on_submit)
        self.visButton.clicked.connect(self.display_plot)

        self.show()

    def on_submit(self):
        # Execute the SQL query here (placeholder function)
        matplotlib.pyplot.close('all')
        query = self.plainTextEdit.toPlainText()
        print(f"Executing SQL Query: {query}")
        
        if is_query_valid(query):
            json_output = execute_query(query, self.connection_params)
            if not json_output['explain_result']:
                print('Invalid query')
                QMessageBox.warning(self, "Error", "Invalid query.")
                self.json_output = None
                return
            # Display the Matplotlib plot
            # self.display_plot(json_output)
            self.json_output = json_output
        else:
            self.json_output = None
            if len(query) == 0:
                QMessageBox.warning(self, "Error", "No input found. Please enter an SQL SELECT query.")
                print('No input found.')
            else:
                QMessageBox.warning(self, "Error", "Forbidden keyword in query. (DELETE, UPDATE, WITH)")
                print('Forbidden keyword in query.')
        
    def display_plot(self):
        # Matplotlib plot
        if not self.json_output:
            QMessageBox.warning(self, "Error", "Please execute a query first.")
            return
        fig, axs = self.create_matplotlib_plot(self.json_output)

        # Opens a new window with the visualization of the first 100 blocks from the first block hit
        fig.show()

    def create_matplotlib_plot(self, json_output):
        self.last_clicked_cell = None
        self.table_to_colour_grids = {}
        block_result = json_output['block_result']
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
                        wrapped_text = textwrap.fill(f"{self.current_lat} Long, {self.current_lon} Lat, Event Long: {event_lon}, Event Lat: {event_lat}, {table_name} Table, {block_data[0][f'{table_name}_ctid']}", width=20)

                        # remove json appending
                        file_path = 'hover_output.json' # Replace with your file path
                        with open(file_path, 'w') as file:
                            json.dump(block_data, file)
                    else:
                        block_data = f'EMPTY BLOCK {block_number} \n{self.current_lat} Long, {self.current_lon} Lat \n Event Long: {event_lon}, Event Lat: {event_lat}'
                        wrapped_text = textwrap.fill(block_data, width=20)
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
            blocks_accessed = json_output['block_dict'][table]
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
    
    