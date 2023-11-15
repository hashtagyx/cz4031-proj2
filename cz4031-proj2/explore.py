import psycopg2
import sqlglot.expressions as exp
from sqlglot import parse_one, exp
import jsonify
import ast
import json
import re

def connect_to_database(params):
    try:
        # Connect to your postgres DB
        conn = psycopg2.connect(
            dbname=params["dbname"],
            user=params["user"],
            password=params["password"],
            host=params["host"]
        )
        return conn
    except psycopg2.OperationalError as e:
        # Handle connection error
        raise psycopg2.OperationalError(f"Database connection failed: {e}")

def execute_query(query, connection_params):
    # Remove all trailing spaces and convert to lowercase
    query = query.lower().strip()
    # Remove all trailing semicolons
    query = query.replace(";", "")
    if query:
        explain_result = run_explain_query(query, connection_params)

        if explain_result == []:
            return {
                'explain_result': [],
                'block_dict': {},
                'block_result': {}
            }

        ctid_result = run_ctid_query(query, connection_params)

        # get fetched blocks and tuples
        block_dict, tuple_dict = get_fetched_blocks_and_tuples(query, ctid_result)

        all_result = all_ctid_query(query, tuple_dict, connection_params)
        block_result = {}
    
        for table_name in all_result:
            block_result[table_name] = []
            column_name = table_name + "_ctid"
            last_block_no = ast.literal_eval(all_result[table_name][0][column_name])[0]
            last_block = []
            for row in all_result[table_name]:
                # converts the string to a tuple
                ctid = ast.literal_eval(row[column_name])
                block_no = ctid[0]
                if last_block_no != block_no:
                    block_result[table_name].append(last_block)
                    last_block = []
                    last_block_no = block_no
                if ctid in tuple_dict[table_name]:
                    row['fetched'] = True
                else:
                    row['fetched'] = False
                last_block.append(row)
            block_result[table_name].append(last_block)

        res =  {
            'explain_result': explain_result, # gives us the explain result needed for QEP tree generation
            'block_dict': block_dict, # gives us the blocks that should be highlighted
            'block_result': block_result # gives us all the tuples of all tables queried in a block-based format
        }
        testoutput = {
            'block_dict': block_dict, # gives us the blocks that should be highlighted
            'block_result': block_result # gives us all the tuples of all tables queried in a block-based format
        }
        file_path = 'output.json' # Replace with your file path
        with open(file_path, 'w') as file:
            json.dump(testoutput, file)
        return res
    # this line will never run because query input is required in interface.py
    return jsonify({'error': 'No query provided'}), 400

def get_fetched_blocks_and_tuples(query, ctid_result):
    table_names = []
    for table in parse_one(query).find_all(exp.Table):
        table_names.append(table.name)
    # this stores the blocks and tuples that have been fetched (block_dict[table_name] and tuple_dict[table_name])
    block_dict = {}
    tuple_dict = {}
    for table_name in table_names:
        block_dict[table_name] = set()
        tuple_dict[table_name] = set()
    
    for row in ctid_result:
        for table_name in table_names:
            column_name = table_name + "_ctid"
            # converts the string to a tuple
            ctid = ast.literal_eval(row[column_name])
            block_no = ctid[0]
            block_dict[table_name].add(block_no)
            tuple_dict[table_name].add(ctid)
    
    for table_name in block_dict:
        block_dict[table_name] = sorted(list(block_dict[table_name]))
        tuple_dict[table_name] = sorted(list(tuple_dict[table_name]))
    
    return block_dict, tuple_dict

def run_explain_query(query, connection_params):
    try:
        conn = psycopg2.connect(**connection_params)
        cur = conn.cursor()
        explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS, COSTS OFF) {query}"
        cur.execute(explain_query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0]
    except (Exception, psycopg2.Error) as error:
        print(f"Error in run_explain_query: {error}")
        return []

def modify_query_add_ctid(sql, table_names):
    rest_of_query = sql[sql.lower().find('select') + len('select'):]
    new_select_clause = "select "

    # For each table, add ctid as a selected column
    for name in table_names:
        new_select_clause += f"{name}.ctid as {name}_ctid, "

    # Check and modify the LIMIT clause
    if 'limit' in rest_of_query.lower():
        # Replace existing LIMIT with 'LIMIT 10000'
        rest_of_query = re.sub(r'LIMIT\s+\d+', 'LIMIT 10000', rest_of_query, flags=re.IGNORECASE)
    else:
        # Append 'LIMIT 10000' if LIMIT clause doesn't exist
        rest_of_query += ' LIMIT 10000'

    # Construct the new query
    new_sql = f"{new_select_clause} {rest_of_query}"

    return new_sql

def get_query_all_ctid(table_name, offset_val):
    new_select_clause = f"""select {table_name}.ctid as {table_name}_ctid, * from {table_name}
     order by {table_name}.ctid limit 10000 offset {offset_val}
    """

    return new_select_clause

def all_ctid_query(query, tuple_dict, connection_params):
    try:
        conn = psycopg2.connect(**connection_params)
        cur = conn.cursor()
        table_names = []
        for table in parse_one(query).find_all(exp.Table):
            table_names.append(table.name)
        
        results = {}
        for table_name in table_names:
            start_block_ctid = tuple_dict[table_name][0]
            
            offset_val_query = f"""
            SELECT rownum FROM (
                SELECT ROW_NUMBER() OVER (ORDER BY ctid) AS rownum, ctid
                FROM {table_name}
            ) AS subquery
            WHERE ctid = '{str(start_block_ctid)}';
            """

            # start_block_number = ast.literal_eval(start_block_ctid)
            # offset_val_query = f"""
            # SELECT rownum FROM (
            #     SELECT ROW_NUMBER() OVER (ORDER BY ctid) AS rownum, ctid
            #     FROM {table_name}
            # ) AS subquery
            # WHERE (ctid::text::point)[0] = {start_block_number}
            # ORDER BY rownum
            # LIMIT 1
            # """

            # print("Start Block Number", start_block_number)
            # print("offset_val_query", offset_val_query)
            
            cur.execute(offset_val_query)
            # the query returns the row number of the first tuple found. hence, we subtract one from the
            # query value to obtain the actual offset value
            offset_val = cur.fetchone()[0] - 1
            
            all_query = f"""
            SELECT array_to_json(array_agg(row_to_json(t))) FROM (
                {get_query_all_ctid(table_name, offset_val)}
            ) t
            """
            cur.execute(all_query)
            result = cur.fetchone()
            results[table_name] = result[0]
        cur.close()
        conn.close()
        return results
    except (Exception, psycopg2.Error) as error:
        print(f"Error in all_ctid_query: {error}")
        return []

def run_ctid_query(query, connection_params):
    try:
        conn = psycopg2.connect(**connection_params)
        cur = conn.cursor()
        table_names = []
        for table in parse_one(query).find_all(exp.Table):
            table_names.append(table.name)
        ctid_query = f"""
        SELECT array_to_json(array_agg(row_to_json(t))) FROM (
            {modify_query_add_ctid(query, table_names)}
        ) t
        """
        # print("CTID QUERY:", ctid_query)
        cur.execute(ctid_query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0]
    except (Exception, psycopg2.Error) as error:
        print(f"Error in run_ctid_query: {error}")
        return []
    
def is_query_valid(query):
    # Check if the query is empty
    if not query.strip():
        return False

    # List of forbidden keywords
    forbidden_keywords = ['delete', 'update', 'with']

    # Check if any forbidden keyword is in the query
    # The query is converted to lowercase to make the check case-insensitive
    if any(keyword in query.lower() for keyword in forbidden_keywords):
        return False

    # If the query passes all checks
    return True