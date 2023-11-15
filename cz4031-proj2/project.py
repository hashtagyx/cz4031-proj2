# Import the App class from the 'interface' module and the 'sys' module
from interface import App
import sys
# Import QApplication from PyQt5, which is needed to create the main application window
from PyQt5.QtWidgets import QApplication

# Define the database connection parameters as a dictionary
# Replace the connection parameters with the user's own credentials
connection_params = {
    "dbname": "TPC-H",       # Name of the database
    "user": "postgres",      # Username to access the database
    "password": "password",  # Password for the database user
    "host": "localhost"      # Host address of the database (here, it's the local machine)
}

if __name__ == '__main__':
    app = QApplication(sys.argv)

    try:
        # Create an instance of the 'App' class (the main application window) with the database connection parameters
        ex = App(connection_params=connection_params)
    except ConnectionError as e:
        # If a ConnectionError occurs (e.g., database connection fails), print the error message and exit the application
        print(e)
        sys.exit(1)

    sys.exit(app.exec_())
