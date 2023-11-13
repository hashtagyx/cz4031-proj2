from explore import execute_query, is_query_valid
import numpy as np
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QMessageBox, QScrollArea
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
        self.title = 'SQL Query Visualizer'
        self.left = 100
        self.top = 100
        self.width = 800
        self.height = 800
        self.current_lat = None
        self.current_lon = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Create textbox
        self.textbox = QLineEdit(self)
        self.textbox.move(20, 20)
        self.textbox.resize(400, 40)

        # Create a button in the window
        self.button = QPushButton('Submit SQL Query', self)
        button_width = 200
        button_height = 40
        # Center the button below the text box
        self.button.setGeometry(
            (self.width - button_width) // 2, 80, 
            button_width, button_height
        )

        # Connect button to function
        self.button.clicked.connect(self.on_submit)

        # Plot area
        self.scroll_area = QScrollArea(self)
        self.plot_widget = QWidget(self)
        self.plot_layout = QVBoxLayout(self.plot_widget)
        self.scroll_area.setWidget(self.plot_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setGeometry(100, 140, self.width - 120, self.height - 160)
        # self.plot_widget.setGeometry(100, 120, 500, 300)

        self.show()

    # def initUI(self):
    #     self.setWindowTitle(self.title)
    #     self.setGeometry(self.left, self.top, self.width, self.height)

    #     # Create textbox
    #     self.textbox = QLineEdit(self)
    #     self.textbox.move(20, 20)
    #     self.textbox.resize(400, 40)

    #     # Create a button in the window
    #     self.button = QPushButton('Submit SQL Query', self)
    #     self.button.move(20, 80)

    #     # Connect button to function
    #     self.button.clicked.connect(self.on_submit)

    #     # Plot area
    #     self.plot_widget = QWidget(self)
    #     self.plot_layout = QVBoxLayout(self.plot_widget)
    #     self.plot_widget.setGeometry(100, 120, 500, 300)

    #     self.show()

    def on_submit(self):
        # Execute the SQL query here (placeholder function)
        query = self.textbox.text()
        print(f"Executing SQL Query: {query}")
        
        if is_query_valid(query):
            json_output = execute_query(query, self.connection_params)
            if not json_output['explain_result']:
                print('Invalid query')
                QMessageBox.warning(self, "Error", "Invalid query.")
                return
            self.display_plot(json_output)
        else:

            QMessageBox.warning(self, "Error", "Forbidden keyword in query. (DELETE, UPDATE, WITH)")
            print('Forbidden keyword in query.')
        # print(json_output)
        # Display the Matplotlib plot
        

    def display_plot(self, json_output):
        # Clear previous plots
        for i in reversed(range(self.plot_layout.count())): 
            self.plot_layout.itemAt(i).widget().setParent(None)

        # Matplotlib plot
        fig, axs = self.create_matplotlib_plot(json_output)
        canvas = FigureCanvas(fig)
        self.plot_layout.addWidget(canvas)

    def create_matplotlib_plot(self, json_output):
        block_result = json_output['block_result']
        num_tables = len(block_result)
        tables = list(block_result.keys())

        fig, axs = plt.subplots(num_tables, 2, figsize=(8, 2 * num_tables), gridspec_kw={'hspace': 0.5})
        
        
        lon_range = np.arange(0, 10, 1)
        lat_range = np.arange(0, 10, 1)


        def on_move(event, ax, table_number):
            if event.inaxes is ax:
                event_lat = floor(event.ydata) if 0 <= event.ydata < len(lat_range) else None
                event_lon = floor(event.xdata) if 0 <= event.xdata < len(lon_range) else None

                # Only update if we have valid coordinates and they are different than the previous update
                if event_lat is not None and event_lon is not None and (event_lat != self.current_lat or event_lon != self.current_lon):
                    self.current_lat = event_lat
                    self.current_lon = event_lon
                    block_number = self.current_lat*10 + self.current_lon
                    if block_number < len(block_result[table_number]):
                        block_data = block_result[table_number][self.current_lat*10 + self.current_lon]
                        # Wrap the text using textwrap
                        wrapped_text = textwrap.fill(f"{table_number} Table, {block_data}", width=20)
                        file_path = 'hover_output.json' # Replace with your file path
                        with open(file_path, 'w') as file:
                            json.dump(block_data, file)
                    else:
                        block_data = f'EMPTY BLOCK {block_number}'
                        wrapped_text = textwrap.fill(block_data, width=20)
                    axs[-1, 1].clear()
                    axs[-1, 1].text(0.5, 0.5, wrapped_text, ha='center', va='center', fontsize=12)
                    axs[-1, 1].axis('off')
                    fig.canvas.draw_idle()

        for i in range(num_tables):

            table = tables[i]
            blocks = block_result[table]
            blocks_accessed = json_output['block_dict'][table]
            blocks_accessed_set = set(blocks_accessed)

            ctid_name = table+'_ctid'
            starting_block = ast.literal_eval(blocks[0][0][ctid_name])[0]

            grid_colour = np.zeros((10, 10))
            for block in range(starting_block, starting_block + 100):
                if block in blocks_accessed_set:
                    block_offset = block - starting_block
                    row = block_offset//10
                    col = block_offset%10
                    grid_colour[row][col] = 1

            mlon, mlat = np.meshgrid(lon_range, lat_range)

            # plot colour mesh Add edgecolors and linewidths to draw borders around cells
            m = axs[i, 0].pcolormesh(mlon, mlat, grid_colour, cmap='Blues', edgecolors='black', linewidths=0.5, vmin=0, vmax=1)

            # Remove colorbar
            cb = fig.colorbar(m, ax=axs[i, 0])
            cb.remove()

            axs[i, 0].set_title(f'Table {table}')

            # Global variables to keep track of which values are currently plotted in ax2
            current_lat, current_lon = None, None

            axs[i, 1].axis('off')

            # Connect the same on_move listener to all graphs
            cid = fig.canvas.mpl_connect('motion_notify_event', lambda event, ax=axs[i, 0], table_number=table: on_move(event, ax, table_number))

        return fig, axs
