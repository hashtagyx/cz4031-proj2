from flask import Flask, request, jsonify
import explore
from flask_cors import CORS

# Connection parameters to pass to the backend
connection_params = {
    "dbname": "TPC-H",
    "user": "postgres",
    "password": "password",
    "host": "localhost"
}

app = Flask(__name__)
CORS(app)

@app.route('/execute-query', methods=['POST'])
def execute_query():
    print('hi')
    data = request.json
    query = data.get('query')
    query = query.lower().strip()
    if query:
        # Use the `explore` module to execute the query and fetch the results
        explain_result = explore.run_explain_query(query, connection_params)
        ctid_result = explore.run_ctid_query(query, connection_params)
        print('done!')
        return jsonify({
            'explain_result': explain_result,
            'ctid_result': ctid_result
        })

    return jsonify({'error': 'No query provided'}), 400

if __name__ == '__main__':
    app.run(debug=True)
