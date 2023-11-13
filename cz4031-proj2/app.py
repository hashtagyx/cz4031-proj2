import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import plotly.graph_objects as go
from plotly.offline import plot
import pandas as pd
import sqlite3
from PyQt5.QtWebEngineWidgets import QWebEngineView
import numpy as np
import matplotlib.pyplot as plt
from math import floor


connection_params = {
    "dbname": "TPC-H",
    "user": "postgres",
    "password": "password",
    "host": "localhost"
}

def execute_query(query):
    # # Process the SQL query here
    # # For demonstration, I'll use a mock dataframe
    # df = pd.DataFrame({
    #     'x': [1, 2, 3, 4, 5],
    #     'y': [2, 3, 4, 5, 6]
    # })

    # # Plotly plot
    # fig1 = go.Figure(data=go.Scatter(x=df['x'], y=df['y']))
    # plot_div = plot(fig1, output_type='div', include_plotlyjs=True)

    # # Matplotlib plot
    # fig2 = Figure()
    # ax = fig2.add_subplot(111)
    # ax.plot(df['x'], df['y'])

    # Coordination
    lon_range = np.arange(0, 25, 1)
    lat_range = np.arange(0, 25, 1)

    # Generate a random 25x25 grid of values
    random_grid = np.random.rand(25, 25)

    # Shade cells blue if valid, else let them be white
    valid_mask = random_grid > 0.5  # Adjust the threshold as needed
    value_1 = np.ones_like(random_grid)  # Set all cells to white initially
    value_1[valid_mask] = 0.5  # Set valid cells to blue

    mlon, mlat = np.meshgrid(lon_range, lat_range)

    # Global variables to keep track of which values
    # are currently plotted in ax2
    current_lat, current_lon = None, None

    fig, (ax1, ax2) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [4, 1]})

    # Add edgecolors and linewidths to draw borders around cells
    m = ax1.pcolormesh(mlon, mlat, value_1, cmap='Blues', edgecolors='black', linewidths=0.5, vmin=0, vmax=1)

    # Remove colorbar
    cb = fig.colorbar(m, ax=ax1)
    cb.remove()

    fig.tight_layout()


    def on_move(event):
        global current_lat, current_lon
        if event.inaxes is ax1:
            event_lat = floor(event.ydata) if 0 <= event.ydata < len(lat_range) else None
            event_lon = floor(event.xdata) if 0 <= event.xdata < len(lon_range) else None

            # Only update if we have valid coordinates and they are different than the previous update
            if event_lat is not None and event_lon is not None and (event_lat != current_lat or event_lon != current_lon):
                current_lat = event_lat
                current_lon = event_lon
                ax2.clear()
                ax2.text(0.5, 0.5, f"Lat: {event_lat}, Lon: {event_lon}", ha='center', va='center', fontsize=12)
                ax2.axis('off')
                fig.canvas.draw_idle()


    cid = fig.canvas.mpl_connect('motion_notify_event', on_move)



    return m

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = 'SQL Query Visualizer'
        self.left = 100
        self.top = 100
        self.width = 640
        self.height = 400
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
        self.button.clicked.connect(self.on_click)

        # Plot area
        self.plot_widget = QWidget(self)
        self.plot_layout = QVBoxLayout(self.plot_widget)
        self.plot_widget.setGeometry(100, 120, 500, 250)
        
        self.show()

    def on_click(self):
        query = self.textbox.text()
        fig2 = execute_query(query)

        # Clear previous plots
        for i in reversed(range(self.plot_layout.count())): 
            self.plot_layout.itemAt(i).widget().setParent(None)

        # Plotly plot
        # plotly_view = QWebEngineView()
        # plotly_view.setHtml(plot_div)

        # self.plot_layout.addWidget(plotly_view)


        # Matplotlib plot
        canvas = FigureCanvas(fig2)
        self.plot_layout.addWidget(canvas)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
