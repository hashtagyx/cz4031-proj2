from interface import App
import sys
from PyQt5.QtWidgets import QApplication

connection_params = {
    "dbname": "TPC-H",
    "user": "postgres",
    "password": "password",
    "host": "localhost"
}

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # add error handling if cannot connect to db, exit the application
    ex = App(connection_params=connection_params)
    sys.exit(app.exec_())
