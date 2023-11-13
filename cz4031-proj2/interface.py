from explore import execute_query
import numpy as np
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from math import floor

class App(QMainWindow):
    def __init__(self, connection_params):
        super().__init__()
        self.connection_params = connection_params
        self.title = 'SQL Query Visualizer'
        self.left = 100
        self.top = 100
        self.width = 640
        self.height = 480
        self.current_lat = None
        self.current_lon = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Create textbox
        self.textbox = QLineEdit(self)
        self.textbox.move(20, 20)
        self.textbox.resize(280, 40)

        # Create a button in the window
        self.button = QPushButton('Submit SQL Query', self)
        self.button.move(20, 80)

        # Connect button to function
        self.button.clicked.connect(self.on_submit)

        # Plot area
        self.plot_widget = QWidget(self)
        self.plot_layout = QVBoxLayout(self.plot_widget)
        self.plot_widget.setGeometry(100, 120, 500, 300)

        self.show()

    def on_submit(self):
        # Execute the SQL query here (placeholder function)
        query = self.textbox.text()
        print(f"Executing SQL Query: {query}")
        # Placeholder for database query execution
        # ...
        json_output = execute_query(query, self.connection_params)
        # add error handling if empty json_output (dont display plot, say smth wrong)
        # print(json_output)
        # Display the Matplotlib plot
        self.display_plot(json_output)

    def display_plot(self, json_output):
        # Clear previous plots
        for i in reversed(range(self.plot_layout.count())): 
            self.plot_layout.itemAt(i).widget().setParent(None)

        # Matplotlib plot
        fig, (ax1, ax2) = self.create_matplotlib_plot(json_output)
        canvas = FigureCanvas(fig)
        self.plot_layout.addWidget(canvas)

    def create_matplotlib_plot(self, json_output):
        ctid_result = json_output['ctid_result']
        length = len(ctid_result)
        sqrt_length = int(length ** 0.5) + 1
        print(sqrt_length, length)
        # Coordination
        lon_range = np.arange(0, sqrt_length, 1)
        lat_range = np.arange(0, sqrt_length, 1)

        # Generate a random 25x25 grid of values
        random_grid = np.random.rand(sqrt_length, sqrt_length)

        # Shade cells blue if valid, else let them be white
        valid_mask = random_grid > 0.5  # Adjust the threshold as needed
        value_1 = np.ones_like(random_grid)  # Set all cells to white initially
        value_1[valid_mask] = 0.5  # Set valid cells to blue

        mlon, mlat = np.meshgrid(lon_range, lat_range)
        fig, (ax1, ax2) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [4, 1]})
        m = ax1.pcolormesh(mlon, mlat, value_1, cmap='Blues', edgecolors='black', linewidths=0.5, vmin=0, vmax=1)
        cb = fig.colorbar(m, ax=ax1)
        cb.remove()
        fig.tight_layout()

        def on_move(event):
            # Event handling logic here
            if event.inaxes is ax1:
                event_lat = floor(event.ydata) if 0 <= event.ydata < len(lat_range) else None
                event_lon = floor(event.xdata) if 0 <= event.xdata < len(lon_range) else None

                # Only update if we have valid coordinates and they are different than the previous update
                if event_lat is not None and event_lon is not None and (event_lat != self.current_lat or event_lon != self.current_lon):
                    self.current_lat = event_lat
                    self.current_lon = event_lon
                    ax2.clear()
                    idx = event_lat * sqrt_length + event_lon
                    
                    ax2.text(0.5, 0.5, idx, ha='center', va='center', fontsize=12)
                    # ax2.text(0.5, 0.5, f"Lat: {event_lat}, Lon: {event_lon}", ha='center', va='center', fontsize=12)
                    ax2.axis('off')
                    fig.canvas.draw_idle()
        cid = fig.canvas.mpl_connect('motion_notify_event', on_move)

        return fig, (ax1, ax2)
