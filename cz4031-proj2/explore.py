import psycopg2
import sqlglot.expressions as exp
from sqlglot import parse_one, exp
import jsonify
import ast
import json
import re

def execute_query(query, connection_params):
    print('hi')
    query = query.lower().strip()
    if query:
        explain_result = run_explain_query(query, connection_params)

        if explain_result == []:
            return {
                'explain_result': [],
                'ctid_result': [],
                'all_result': []
            }

        ctid_result = run_ctid_query(query, connection_params)
        all_result = all_ctid_query(query, connection_params)
        # print("explain_result", explain_result)
        # print("ctid_result", ctid_result)
        # print("all_result,", all_result)
        # print('done!')

        # replace this with a function
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

        block_result = {}
    
        for table_name in all_result:
            block_result[table_name] = []
            last_block_no = 0
            last_block = []
            for row in all_result[table_name]:
                column_name = table_name + "_ctid"
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
            'ctid_result': ctid_result, # gives us the ctid result of the query
            'all_result': all_result, # gives us all the tuples of all tables queried
            'block_dict': block_dict, # gives us the blocks that should be highlighted
            'block_result': block_result # gives us all the tuples of all tables queried in a block-based format
        }
        testoutput = {
            'block_dict': block_dict, # gives us the blocks that should be highlighted
            'block_result': block_result # gives us all the tuples of all tables queried in a block-based format
        }
        file_path = 'C:\\Users\\cyx_9\\Desktop\\DB Project 2\\cz4031-proj2\\output.json' # Replace with your file path
        with open(file_path, 'w') as file:
            json.dump(testoutput, file)

        # print("RES OUTPUT:", res)
        return res
    # this line will never run because query input is required in index.html
    return jsonify({'error': 'No query provided'}), 400

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

def modify_query_all_ctid(table_name):
    new_select_clause = f"select {table_name}.ctid as {table_name}_ctid, * from {table_name} order by {table_name}.ctid limit 10000"

    return new_select_clause

def all_ctid_query(query, connection_params):
    try:
        conn = psycopg2.connect(**connection_params)
        cur = conn.cursor()
        table_names = []
        for table in parse_one(query).find_all(exp.Table):
            table_names.append(table.name)
        
        results = {}
        for table_name in table_names:
            all_query = f"""
            SELECT array_to_json(array_agg(row_to_json(t))) FROM (
                {modify_query_all_ctid(table_name)}
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
        cur.execute(ctid_query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0]
    except (Exception, psycopg2.Error) as error:
        print(f"Error in run_ctid_query: {error}")
        return []
    
