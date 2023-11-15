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

    try:
        ex = App(connection_params=connection_params)
    except ConnectionError as e:
        print(e)
        sys.exit(1)

    sys.exit(app.exec_())
