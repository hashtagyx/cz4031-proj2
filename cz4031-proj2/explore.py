# Import necessary modules
import psycopg2
import sqlglot.expressions as exp
from sqlglot import parse_one, exp
import jsonify
import ast
import re

# Connects to the local PostgreSQL database with the provided parameters
def connect_to_database(params):
    try:
        # Connect to your PostgreSQL DB
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

# Executes a given SQL query using the provided connection parameters
# Returns a dictionary/JSON object:
# {
#     'explain_result': JSON array containing the output from an EXPLAIN query
#     'block_dict': JSON object containing the blocks accessed by each table in the query. Keys are the table name and values are the list of block numbers accessed.
#     'block_result': JSON object containing the tuples of each table in the query. Keys are the table names, values are the list of blocks of each table. Within each list of blocks are the individual tuple entries.
# }
def execute_query(query, connection_params):
    # Preprocessing the query: stripping leading/trailing spaces, standardise use of '', remove semicolon
    query = query.strip()
    query = query.replace('"', "'") # ensures all string-based conditional statements work
    query = query.replace(";", "")

    # Execute the query if it's not empty
    if query:
        # Run the EXPLAIN query to get the execution plan
        explain_result = run_explain_query(query, connection_params)

        # If there's no result from the EXPLAIN query, return empty data (botched query submitted)
        if not explain_result:
            return {
                'explain_result': [],
                'block_dict': {},
                'block_result': {}
            }

        # Run query to get the CTID values (tuple identifiers in PostgreSQL)
        ctid_result = run_ctid_query(query, connection_params)

        # If there's no result from the CTID query, return empty data (botched query submitted)
        if not ctid_result:
            return {
                'explain_result': [],
                'block_dict': {},
                'block_result': {}
            }

        # Obtain the fetched blocks and tuples from the original query
        block_dict, tuple_dict = get_fetched_blocks_and_tuples(query, ctid_result)

        # Run a query to get all CTID values of blocks
        all_result = all_ctid_query(query, tuple_dict, connection_params)

        # Process all_result with tuple_dict to get block_result. block_result[table_name] is a list of blocks of the table table_name.
        # block_result[table_name][i] is a list of rows/tuples in the ith block.
        # block_result[table_name][i][j] is the jth tuple in the ith block.
        block_result = get_block_result(tuple_dict, all_result)

        res =  {
            'explain_result': explain_result, # Gives us the EXPLAIN result needed for QEP tree generation
            'block_dict': block_dict, # Gives us the block numbers that should be highlighted
            'block_result': block_result # Gives us all the tuples of all tables queried in a block-based format
        }

        return res
    
    # This line will never run because query input is required in interface.py
    return jsonify({'error': 'No query provided'}), 400

# Process all_result with tuple_dict to get block_result
def get_block_result(tuple_dict, all_result):
    block_result = {}
    
    for table_name in all_result:
         # Initialize an empty list for each table in the block_result dictionary to represent a list of blocks
        block_result[table_name] = []
        # Construct the column name for CTID
        column_name = table_name + "_ctid"

        # Get the block number of the first tuple in the first block of the current table
        last_block_no = ast.literal_eval(all_result[table_name][0][column_name])[0]
        # Initialize an empty list to store tuples belonging to the same block
        last_block = []

        for row in all_result[table_name]:
            # Convert the CTID string in the row to a tuple (block number, tuple number)
            ctid = ast.literal_eval(row[column_name])
            block_no = ctid[0]

            # If the block number changes, append the last block to the result and start a new block
            if last_block_no != block_no:
                block_result[table_name].append(last_block)
                last_block = []
                last_block_no = block_no
            
            # Check if the current tuple's CTID is in the set of fetched tuples
            if ctid in tuple_dict[table_name]:
                row['fetched'] = True # Mark the tuple as fetched
            else:
                row['fetched'] = False # Mark the tuple as not fetched
            
            # Add the current row to the last block
            last_block.append(row)
        
        # Append the last block to the block_result after finishing the loop
        block_result[table_name].append(last_block)
    return block_result

# Obtain the blocks and tuples that have been fetched from disk given the query and CTID query result
def get_fetched_blocks_and_tuples(query, ctid_result):
    table_names = []
    # Parse the query to find all the table names
    for table in parse_one(query).find_all(exp.Table):
        table_names.append(table.name)

    # Initialize dictionaries to store the blocks and tuples that have been fetched
    block_dict = {}
    tuple_dict = {}
    for table_name in table_names:
        block_dict[table_name] = set() # Set to store unique block numbers
        tuple_dict[table_name] = set() # Set to store unique CTIDs
    
    # Iterate through each row in the CTID result
    for row in ctid_result:
        # Process each table's fetched blocks and tuples
        for table_name in table_names:
            column_name = table_name + "_ctid" # Construct the CTID column name for the table

            # Converts the CTID string in the row to a tuple (block number, tuple number)
            ctid = ast.literal_eval(row[column_name])
            block_no = ctid[0]

            # Add the block number and CTID to their respective sets in the dictionaries
            block_dict[table_name].add(block_no)
            tuple_dict[table_name].add(ctid)
    
    # Convert the sets in block_dict and tuple_dict to sorted lists (so that we can return it as a valid JSON object)
    for table_name in block_dict:
        block_dict[table_name] = sorted(list(block_dict[table_name]))
        tuple_dict[table_name] = sorted(list(tuple_dict[table_name]))
    
    return block_dict, tuple_dict

# Runs the EXPLAIN query in PostgreSQL and returns the result
def run_explain_query(query, connection_params):
    try:
        # Connect to the PostgreSQL database using the provided connection parameters
        conn = psycopg2.connect(**connection_params)
        cur = conn.cursor()

        # Generate the EXPLAIN query by prepending the original query
        explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS, COSTS OFF) {query}"

        # Execute the EXPLAIN query
        cur.execute(explain_query)

        # Fetch the first row of the result set (the query plan in JSON format)
        result = cur.fetchone()

        # Close the cursor and the connection
        cur.close()
        conn.close()

        # Return the query plan (first element of the result tuple)
        return result[0]
    # Handle exceptions during query execution or connection issues
    except (Exception, psycopg2.Error) as error:
        # Print the error and return an empty list as the result
        print(f"Error in run_explain_query: {error}")
        return []

# Modifies SQL query by adding CTID selection for each table. Note: 10000 tuple limit for performance.
def modify_query_add_ctid(sql, table_names):
    # Extract the part of the SQL query after 'SELECT' (ignoring case)
    rest_of_query = sql[sql.lower().find('select') + len('select'):]

    # Start constructing a new SELECT clause
    new_select_clause = "select "

    # For each table, add CTID as a selected column, with the name <table_name>_ctid
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

# Construct a SQL query that retrieves CTID values and all other columns for a specific table subject to an offset
# This fetches the first 10000 tuples in ascending CTID values from the specified table following the offset such that the first tuple returned is in the first block hit
def get_query_all_ctid(table_name, offset_val):
    new_select_clause = f"""select {table_name}.ctid as {table_name}_ctid, * from {table_name}
     order by {table_name}.ctid limit 10000 offset {offset_val}
    """

    return new_select_clause

# Execute queries for CTID values for all tables in the original query, starting from the first block hit
# Note the LIMIT 10000 in get_query_all_ctid which limits the number of tuples returned for performance purposes
def all_ctid_query(query, tuple_dict, connection_params):
    try:
        # Establish a connection to the database
        conn = psycopg2.connect(**connection_params)
        cur = conn.cursor()

        # Extract table names from the given query
        table_names = []
        for table in parse_one(query).find_all(exp.Table):
            table_names.append(table.name)
        
        results = {}

        # Process each table involved in the query
        for table_name in table_names:
            # Get the CTID of the first block hit in the original query from tuple_dict
            start_block_ctid = tuple_dict[table_name][0]
            # Extract the block number of the first block hit in the original query
            start_block_number = start_block_ctid[0]

            # Construct a query to find the row number of the first tuple in the first block hit in the original query
            offset_val_query = f"""
            SELECT rownum FROM (
                SELECT ROW_NUMBER() OVER (ORDER BY ctid) AS rownum, ctid
                FROM {table_name}
            ) AS subquery
            WHERE (ctid::text::point)[0] = {start_block_number}
            ORDER BY rownum
            LIMIT 1
            """

            # Execute the query to find the offset value
            cur.execute(offset_val_query)
            # The query returns the row number of the first tuple found. Hence, we subtract one from the
            # query value to obtain the actual offset value
            offset_val = cur.fetchone()[0] - 1
            
            # Construct the final query using the offset value to find all* the tuples in the table (*subject to LIMIT 10000 and OFFSET to the first block hit)
            all_query = f"""
            SELECT array_to_json(array_agg(row_to_json(t))) FROM (
                {get_query_all_ctid(table_name, offset_val)}
            ) t
            """
            # Execute the final query to get the CTIDs and their corresponding row data
            cur.execute(all_query)
            result = cur.fetchone()
            # Store the result in the results dictionary
            results[table_name] = result[0]

        cur.close()
        conn.close()
        return results
    # Handle exceptions that may occur during database operations
    except (Exception, psycopg2.Error) as error:
        # Print the error message and return and empty dictionary
        print(f"Error in all_ctid_query: {error}")
        return {}

# Execute a modified version of the input query that includes CTID selection
def run_ctid_query(query, connection_params):
    try:
        # Establish a connection to the PostgreSQL database using the provided connection parameters
        conn = psycopg2.connect(**connection_params)
        cur = conn.cursor()

        # Extract table names from the given query
        table_names = []
        for table in parse_one(query).find_all(exp.Table):
            table_names.append(table.name)

        # Modify the input query to include CTID selection for each table
        # The modified query selects CTIDs along with all other columns
        ctid_query = f"""
        SELECT array_to_json(array_agg(row_to_json(t))) FROM (
            {modify_query_add_ctid(query, table_names)}
        ) t
        """
        # Execute the modified query
        cur.execute(ctid_query)

        # Fetch the first row from the query result
        result = cur.fetchone()
        cur.close()
        conn.close()

        # Return the result of the query (the first element of the result tuple)
        return result[0]
    # Handle exceptions that might occur during database operations
    except (Exception, psycopg2.Error) as error:
        # Print the error message and return an empty list is there is an error
        print(f"Error in run_ctid_query: {error}")
        return []

# Check if input query is valid (i.e. no forbidden keyword, non empty)
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