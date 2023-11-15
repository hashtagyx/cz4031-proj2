# Import necessary modules
from explore import execute_query, is_query_valid, connect_to_database
import numpy as np
from PyQt5 import QtWidgets, QtWebEngineWidgets
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QScrollArea, QLabel, QComboBox, QTextBrowser, QTableWidget, QTableWidgetItem, QHeaderView
import matplotlib
import matplotlib.pyplot as plt
import ast
from igraph import Graph
import plotly.graph_objects as go

# Define the App class which inherits from QMainWindow
class App(QMainWindow):
    def __init__(self, connection_params):
        super().__init__()
        self.connection_params = connection_params

        # Try to establish a connection to the database
        try:
            self.db_connection = connect_to_database(connection_params)
            print("Connected to the database successfully")
        except Exception as e:
            # If connection fails, raise a ConnectionError with the error message
            raise ConnectionError(f"Failed to connect to database: {e}")
        
        # Initialize various attributes
        self.title = 'SQL Query Visualizer' # Window Title
        self.data = None # Variable to store query results
        self.current_lat = None  # Current latitude of mouse cursor
        self.current_lon = None  # Current longitude of mouse cursor
        self.table_to_colour_grids = {}  # Stores color grids for visualizing table data
        self.last_clicked_cell = None  # Stores the last clicked cell in the visualization
        self.selected_relation = None  # Currently selected table/relation
        self.qep_figure = None  # Query Execution Plan figure

        # Initialize the UI
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)  # Set the window title
        self.resize(800, 400)  # Set the window size
        self.move(100, 100)  # Position the window on the screen
        
        # Create a central widget for the main window
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")

        # Create a vertical layout for the central widget
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout.setObjectName("verticalLayout")

        # Add label for the SQL query input
        self.label = QtWidgets.QLabel("Enter SQL Query Here:")
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)

        # Add a plain text edit widget for SQL query input
        self.plainTextEdit = QtWidgets.QPlainTextEdit()
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.plainTextEdit.setMaximumHeight(100)
        self.verticalLayout.addWidget(self.plainTextEdit)

        # Add an 'Execute Query' button
        self.exeButton = QtWidgets.QPushButton("Execute Query")
        self.exeButton.setObjectName("exeButton")
        self.verticalLayout.addWidget(self.exeButton)

        # Add horizontal layout for other buttons
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        # Add view QEP button to the horizontal layout
        self.qepButton = QtWidgets.QPushButton("View Query Execution Plan")
        self.qepButton.setObjectName("qepButton")
        self.horizontalLayout.addWidget(self.qepButton)

        # Add visualize button to the horizontal layout
        self.visButton = QtWidgets.QPushButton("Visualize Sampled Blocks")
        self.visButton.setObjectName("visButton")
        self.horizontalLayout.addWidget(self.visButton)

        # Add horizontal layout to the main vertical layout
        self.verticalLayout.addLayout(self.horizontalLayout)

        # Initialize labels and dropdowns for selecting relations (tables) and block IDs
        self.select_relation = QLabel("Select Relation:")
        self.select_block_id = QLabel("Select Block ID:")
        # Initialize QTextBrowser to view tuples in selected block
        self.block_tuple_viewer = QTextBrowser()

        # ComboBox for selecting a relation (table). Initially disabled.
        self.relation_selector = QComboBox()
        self.relation_selector.setEnabled(False) # Disable the ComboBox until it's populated
        # Connect the relation_selector's change event to update_relation_selector method
        self.relation_selector.currentTextChanged.connect(lambda relation: self.update_relation_selector(relation))

        # ComboBox for selecting a block ID. Initially disabled.
        self.block_id_selector = QComboBox()
        self.block_id_selector.setEnabled(False) # Disable the ComboBox until it's populated
        # Connect the block_id_selector's change event to display_curr_block_contents method
        self.block_id_selector.currentTextChanged.connect(lambda block_id: self.display_curr_block_contents(block_id))

        # Initialize table and scroll area as instance variables
        self.table = None
        self.scroll_area = None

        # Add the labels and ComboBox widgets to the vertical layout of the central widget
        self.verticalLayout.addWidget(self.select_relation)
        self.verticalLayout.addWidget(self.relation_selector)
        self.verticalLayout.addWidget(self.select_block_id)
        self.verticalLayout.addWidget(self.block_id_selector)

        # Connecting buttons to their functions
        self.exeButton.clicked.connect(self.on_submit)
        self.visButton.clicked.connect(self.display_plot)
        self.qepButton.clicked.connect(self.display_qep)

        # Set the central widget
        self.setCentralWidget(self.centralwidget)

        # Show the main window
        self.show()

    # When the `Execute Query`/exeButton is triggered, runs the SQL queries in the backend
    def on_submit(self):
        # Retrieve the SQL query from the plain text edit widget
        query = self.plainTextEdit.toPlainText()
        print(f"Executing SQL Query: {query}")
        
        # Check if the SQL query is valid
        if is_query_valid(query):
            # Execute the query using the given connection parameters and store the results
            data = execute_query(query, self.connection_params)

            # Check if the query execution result is valid (i.e., if the EXPLAIN result is present)
            if not data['explain_result']:
                # If the query is invalid, display an error message and reset data
                print('Invalid query')
                QMessageBox.warning(self, "Error", "Invalid query.")
                self.data = None
                return

            # If the query is valid, update the class attribute with the query results
            self.data = data

             # Extract the list of relations (tables) involved in the query from the block_dict keys
            relations = list(data['block_dict'].keys())

            # Clear the existing items in the relation_selector ComboBox and populate it with new relations
            self.relation_selector.clear()
            self.relation_selector.addItems(relations)
            self.relation_selector.setEnabled(True)
        else:
            # If the query is not valid, reset data
            self.data = None
            # Check if the query is empty
            if len(query) == 0:
                # Display an error message if no query is entered
                QMessageBox.warning(self, "Error", "No input found. Please enter an SQL SELECT query.")
                print('No input found.')
            else:
                # Display an error message if the query contains forbidden keywords
                QMessageBox.warning(self, "Error", "Forbidden keyword in query. (DELETE, UPDATE, WITH)")
                print('Forbidden keyword in query.')

    # Updates the block ID selector ComboBox when a new relation (table) is selected.
    def update_relation_selector(self, relation):
        # Update the currently selected relation (table)
        self.selected_relation = relation

        # If the selected relation is empty (no selection), return immediately
        if self.selected_relation == '':
            return

        # Retrieve the block IDs that were accessed for the selected relation
        block_ids = self.data['block_dict'][relation]

        # Get the first and last block numbers from the block results for the selected relation 
        last_block = ast.literal_eval(self.data['block_result'][relation][-1][-1][f"{relation}_ctid"])[0]
        first_block = ast.literal_eval(self.data['block_result'][relation][0][0][f"{relation}_ctid"])[0]
        
        # Create a list of block IDs starting from the first block to the last block (inclusive)
        block_ids = [x for x in range(first_block, last_block+1)]

        # Convert the block IDs to strings for display in the ComboBox
        block_ids = list(map(str, block_ids))

        # Clear any existing items in the block ID selector ComboBox
        self.block_id_selector.clear()
        # Add the new list of block IDs to the ComboBox
        self.block_id_selector.addItems(block_ids)
        # Enable the block ID selector ComboBox
        self.block_id_selector.setEnabled(True)

    # Displays content of the selected block in a table, called when the user selects a specific block_id to display
    def display_curr_block_contents(self, block_id):
        # Check if a relation and block ID have been selected
        if self.selected_relation is not None and block_id != '':
            # Get the smallest index (block number) for the selected relation
            smallest_index = self.data['block_dict'][self.selected_relation][0]
            # Calculate the index for the selected block ID
            index = int(block_id) - smallest_index
            # Get the content of the block for the selected relation at the calculated index
            block_content = self.data['block_result'][self.selected_relation][index]

            # Clear existing content in the QTextBrowser
            self.block_tuple_viewer.clear()

            # Display the content in a table
            self.display_table(block_content)

    # Creates and populates a table widget with the content of a block, called in `display_curr_block_contents`
    def display_table(self, block_content):
        # Check if the block content is not empty
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
                # Create a table item for each piece of data and add it to the table
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

        # Resize the window to accommodate the new content
        self.resize(max(self.width(), 800), max(self.height(), 800))

    # Handles the visualization of the blocks accessed by the SQL query, when visButton is clicked
    def display_plot(self):
        # Close any existing Matplotlib plots to prevent clutter
        matplotlib.pyplot.close('all')

        # Check if data from the executed SQL query exists
        if not self.data:
            QMessageBox.warning(self, "Error", "Please execute a query first.")
            return
        
        # Generate the Matplotlib plot based on the query data
        fig, axs = self.create_matplotlib_plot(self.data)

        # Opens a new window with the visualization of the first 100 blocks from the first block hit
        fig.show()

    # Creates a Matplotlib plot for visualizing the blocks accessed by the SQL query
    # Helper function used in `display_plot`
    def create_matplotlib_plot(self, data):
        # Reset the last clicked cell and color grids
        self.last_clicked_cell = None
        self.table_to_colour_grids = {}

        # Extract block result data for plotting
        block_result = data['block_result']
        num_tables = len(block_result)
        tables = list(block_result.keys())

        # Create a Matplotlib subplot for each table involved in the query
        fig, axs = plt.subplots(num_tables, 2, figsize=(8, 2 * num_tables), gridspec_kw={'hspace': 0.5})
        
        # Define ranges for the mesh grid visualization (10 * 10 == 100 blocks used for visualization)
        lon_range = np.arange(0, 10, 1)
        lat_range = np.arange(0, 10, 1)

        # Define a lambda function to handle mouse movement over the plot
        def make_on_move_lambda(ax, table_name, grid_colour, m):
            return lambda event: on_move(event, ax, table_name, grid_colour, m)

        # Define the on_move function to update the plot based on mouse click event ('button_press_event')
        def on_move(event, ax, table_name, grid_colour, m):
            if event.inaxes is ax:
                # Determine the coordinates of the mouse click event
                event_lat = event.ydata if -0.5 <= event.ydata < len(lat_range) else None
                event_lon = event.xdata if -0.5 <= event.xdata < len(lon_range) else None

                # Only update if we have valid coordinates and they are different than the previous update
                if event_lat is not None and event_lon is not None and (event_lat != self.current_lat or event_lon != self.current_lon):
                    self.current_lat = round(event_lat)
                    self.current_lon = round(event_lon)
                    block_number = self.current_lat * 10 + self.current_lon

                    # Retrieve block data for the given coordinates
                    if block_number < len(block_result[table_name]):
                        block_data = block_result[table_name][self.current_lat * 10 + self.current_lon]
                        block_number = ast.literal_eval(block_data[0][f"{table_name}_ctid"])[0]
                        no_of_tuples = len(block_data)
                        count_true = sum(1 for entry in block_data if entry.get("fetched"))

                        # Generate text to display block information
                        display_text = f"Table Name: {table_name}\nCurrent Block: {block_number}\nNumber of Tuples in Block: {no_of_tuples}\nNumber of Tuples Hit: {count_true}"
                    else:
                        # Handle empty blocks
                        display_text = f'Table Name: {table_name}\nCurrent Block: {block_number}\nEmpty Block'

                    # Display block information on the plot
                    # axs is 2-dimensional if there is more than one table; handling these cases differently
                    if num_tables > 1:
                        axs[-1, 1].clear()
                        axs[-1, 1].text(0.5, 0.5, display_text, ha='center', va='center', fontsize=12)
                        axs[-1, 1].axis('off')
                    else:
                        axs[1].clear()
                        axs[1].text(0.5, 0.5, display_text, ha='center', va='center', fontsize=12)
                        axs[1].axis('off')
                    fig.canvas.draw_idle()

                x_index = int(event.xdata + 0.5)
                y_index = int(event.ydata + 0.5)
                
                # Update the color of the clicked cell and restore the color of the previous cell
                if 0 <= x_index < grid_colour.shape[1] and 0 <= y_index < grid_colour.shape[0]:
                    # Restore the color of last click (if it exists)
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

        # Generate the plot for each table
        for i in range(num_tables):
            if num_tables > 1:
                ax = axs[i, 0]  # Use two indices if axs is 2D
                axs[i, 1].clear()
                axs[i, 1].axis('off')
            else:
                ax = axs[0]  # Use one index if axs is 1D
                axs[1].clear()
                axs[1].axis('off')

            # Retrieve the current table name and its blocks data
            table = tables[i]
            blocks = block_result[table]
            blocks_accessed = data['block_dict'][table]
            blocks_accessed_set = set(blocks_accessed)

            # Construct the column name for CTID and find the starting block for the current table
            ctid_name = table + '_ctid'
            starting_block = ast.literal_eval(blocks[0][0][ctid_name])[0]

            # Initialize a grid for color mapping
            grid_colour = np.zeros((10, 10)) # 10*10 grid with zeros
            for block in range(starting_block, starting_block + 100):
                if block in blocks_accessed_set:
                    # Calculate the row and column in the grid for the accessed block and assign a new color to mark it
                    block_offset = block - starting_block
                    row = block_offset // 10
                    col = block_offset % 10
                    grid_colour[row][col] = 1

            # Create a meshgrid for plotting
            mlon, mlat = np.meshgrid(lon_range, lat_range)

            # Plot a color mesh, add edgecolors and linewidths for cell borders
            m = ax.pcolormesh(mlon, mlat, grid_colour, cmap='Blues', edgecolors='black', linewidths=0.5, vmin=0, vmax=1)
            self.table_to_colour_grids[table] = (m, grid_colour) # Store the mesh and initial grid_colour so that we can revert any clicked cell to its original colour

            # Set the title for the subplot
            ax.set_title(f'Table Name: {table}')
            
            # Connect a mouse event listener to the plot for interactive response
            on_move_lambda = make_on_move_lambda(ax, table, grid_colour, m)
            cid = fig.canvas.mpl_connect('button_press_event', on_move_lambda)

        # Return the figure and the axes for display
        return fig, ax
    
    # Generates and returns the QEP figure for the last query
    def QEP(self):
        # Define attributes that will be added as node attributes in the graph
        qep_attrs = ['Relation Name', 'Hash Cond', 'Merge Cond', 'Join Type', 'Shared Hit Blocks', 'Filter', 'Rows Removed by Filter']

        # Function to add attributes to a graph node
        def add_attr(ptr, g, attrs):
            # Assign the name of the node
            g.vs[ptr]['name'] = attrs['Node Type']
            # Add other relevant attributes
            for attr in qep_attrs:
                if attr in attrs:
                    g.vs[ptr][attr] = attrs[attr]

        # Extract the plan data from the query execution plan result
        result_data = self.data['explain_result'][0]

        # Initialize a graph
        g = Graph()
        g.add_vertex()
        # Add attributes to the root vertex
        add_attr(0, g, result_data['Plan'])

        # Initialize a pointer to keep track of the current node ID
        ptr = 0

        # Process the sub-plans if they exist using level-order traversal
        if 'Plans' in result_data['Plan']:
            temp_result = [(0, result_data['Plan']['Plans'])] # List of tuples (parent ID, plan)
            while len(temp_result) > 0: # temp_result is a list
                parent, loop_result = temp_result.pop(0)
                for p in loop_result[:]: # p is a dict
                    ptr += 1
                    g.add_vertex()
                    g.add_edge(ptr, parent) # Manually add an edge to the graph
                    add_attr(ptr, g, p) # Add attributes to the current node

                    # Add the current node's children if they exist
                    if 'Plans' in p:
                        temp_result.append((ptr, p['Plans']))

        # Extract labels (node names) from the graph vertices
        labels = list(g.vs['name'])
        N = len(labels) # Number of nodes in the graph
        E = [e.tuple for e in g.es] # List of edges as tuples (source, target)

        # Generate coordinates for each node in the graph
        layt = g.layout('rt', root=[0])
        Xn = [layt[k][0] for k in range(N)] # X-coordinates of nodes
        Yn = [layt[k][1] for k in range(N)] # Y-coordinates of nodes

        # Prepare edges for plotting
        Xe = []
        Ye = []
        for e in E:
            # Add the coordinates for each edge's start and end points, followed by None to separate edges
            Xe += [layt[e[0]][0], layt[e[1]][0], None]
            Ye += [layt[e[0]][1], layt[e[1]][1], None]

        # Prepare hover labels for each node
        hoverlabels = []
        for i in range(N):
            hoverlabel = ''
            for j in qep_attrs:
                try:
                    # If the attribute exists, append it to the hover label
                    if g.vs[i][j] is not None:
                        hoverlabel = hoverlabel + '<br>' +  j + ': ' + str(g.vs[i][j])
                    # Special handling for 'Shared Hit Blocks' attribute
                    if j == 'Shared Hit Blocks':
                        blocks = int(g.vs[i][j])
                        block_size = 8192 # Block size for calculation
                        # Calculate and append total number of bytes hit in the blocks
                        hoverlabel = hoverlabel + '<br>' + 'Total num of blocks hit in Bytes: ' + str(block_size * blocks)
                except:
                    continue
            hoverlabels.append(hoverlabel) # Add the hover label for the current node

        fig = go.Figure()
        # Add edges to the figure as lines
        fig.add_trace(go.Scatter(x=Xe,
                            y=Ye,
                            mode='lines',
                            name='',
                            line=dict(color='rgb(210,210,210)', width=1),
                            hoverinfo='none'
                            ))
        # Add nodes to the figure as markers+text
        fig.add_trace(go.Scatter(x=Xn,
                            y=Yn,
                            mode='markers+text',
                            name='',
                            marker=dict(symbol='line-ew',
                                        size=18,
                                        color='#6175c1',
                                        line=dict(color='#ffffff', width=1)
                                        ),
                            text=labels,
                            textposition='middle center',
                            hoverinfo='text',
                            customdata = np.stack(hoverlabels, axis =-1),
                            hovertemplate="%{customdata}",
                            opacity=0.8
                            ))

        # Update the figure layout
        fig.update_layout(
            showlegend=True,
            hovermode="closest",
            margin=dict(b=0, l=0, r=0, t=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, autorange="reversed"),
        )

        return fig

    # Displays the QEP tree in a new window, called when `qepButton` is clicked
    def display_qep(self):
        # Check if data is available before plotting
        if not self.data:
            QMessageBox.warning(self, "Error", "Please execute a query first.")
            return
        # Generate the QEP figure
        self.qep_figure = self.QEP()

        # Create a dialog window to display the QEP
        pop_up_dialog = QtWidgets.QDialog(self)
        pop_up_dialog.setWindowTitle('Query Execution Plan')
        pop_up_dialog.resize(700,500)

        # Embed a QWebEngineView for the figure in the pop-up dialog
        pop_up_browser = QtWebEngineWidgets.QWebEngineView(pop_up_dialog)
        pop_up_browser.setHtml(self.qep_figure.to_html(include_plotlyjs='cdn'))

        # Set layout for the pop-up dialog
        layout = QtWidgets.QVBoxLayout(pop_up_dialog)
        layout.addWidget(pop_up_browser)

        # Show the pop-up dialog
        pop_up_dialog.exec_()