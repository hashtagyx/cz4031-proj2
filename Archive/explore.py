import psycopg2
import json
import sqlglot 
import sqlglot.expressions as exp
from sqlglot import parse_one, exp

# tables = []
# # find all tables (x, y, z)
# for table in parse_one("SELECT * FROM x JOIN y JOIN z").find_all(exp.Table):
#     tables.append(table.name)
# print("tables:", tables)

def run_explain_query(query, connection_params):
    conn = psycopg2.connect(**connection_params)
    cur = conn.cursor()
    explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS, COSTS OFF) {query}"
    cur.execute(explain_query)
    result = cur.fetchone()
    cur.close()
    conn.close()
    # print("explain query:",result)
    return result[0]

def modify_query_add_ctid(sql, table_names):
    rest_of_query = sql[sql.lower().find('select') + len('select'):]
    new_select_clause = "select "

    # For each table, add ctid as a selected column
    for name in table_names:
        new_select_clause += f"{name}.ctid as {name}_ctid, "

    # Construct the new query
    new_sql = f"{new_select_clause} {rest_of_query}"

    return new_sql

def run_ctid_query(query, connection_params):
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
    # print("ctid query:",result)
    return result[0]
    
