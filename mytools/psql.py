# AUTOGENERATED! DO NOT EDIT! File to edit: ../00_psql.ipynb.

# %% auto 0
__all__ = ['query', 'schema', 'LocalBase', 'docker_run', 'pgdump', 'pgrestore', 'get_constraints', 'du', 'dtypes', 'current',
           'kill', 'insert_on_conflict', 'read_sql']

# %% ../00_psql.ipynb 2
from sqlalchemy import create_engine
from sqlalchemy import DateTime
from sqlalchemy import Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Date, String, Text, Float, Boolean, ForeignKey, and_, or_, MetaData
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy import update
from sqlalchemy import desc
import pandas as pd
import datetime
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import select, exists
from IPython.display import clear_output
from sqlalchemy import Column, Integer, String ,DateTime,UniqueConstraint,Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql.sqltypes import *
from sqlalchemy import *
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import Executable, ClauseElement #_literal_as_text
from sqlalchemy.ext import compiler
from sqlalchemy.schema import DDLElement
from sqlalchemy.inspection import inspect
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import VARCHAR

from sqlalchemy.dialects.postgresql import JSON

from sqlalchemy.dialects.postgresql import REAL

from sqlalchemy import cast

# %% ../00_psql.ipynb 3
def docker_run(docker_name,passw,port): 
    return f'sudo docker run --name {docker_name} -e POSTGRES_PASSWORD={passw} -d -p {port}:5432  -v {docker_v_path} postgres'


def pgdump(schema,passw,port):    
    now = pd.Timestamp.now()
    return f"pg_dump postgresql://postgres:{passw}@localhost:{port} -n {schema} > {schema}_{now.hour}_{now.day}_{now.month}_{now.year}.sql"

def pgrestore(docker_name, dump_path = False):
    if not dump_path:
        dumps = path_info(psql_backup_path).sort_values('time')
        dump_path = dumps[dumps['name'].str.contains(".sql")].iloc[-1]['path']
    
    return f'cat {dump_path} | docker exec -i {docker_name} psql -U postgres | >> log.log'

# %% ../00_psql.ipynb 4
def get_constraints():
    return pd.read_sql("""SELECT conrelid::regclass AS table_from
                          ,conname
                          ,pg_get_constraintdef(c.oid)
                    FROM   pg_constraint c
                    JOIN   pg_namespace n ON n.oid = c.connamespace
                    AND    n.nspname = 'public' -- your schema here
                    ORDER  BY conrelid::regclass::text, contype DESC;""",engine)

# %% ../00_psql.ipynb 5
def du(partitions='no'):

    df = query("""SELECT *, pg_size_pretty(total_bytes) AS total
                            , pg_size_pretty(index_bytes) AS INDEX
                            , pg_size_pretty(toast_bytes) AS toast
                            , pg_size_pretty(table_bytes) AS TABLE
                          FROM (
                          SELECT *, total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes FROM (
                              SELECT c.oid,
                                     nspname AS table_schema,
                                     relname AS TABLE_NAME
                                      , c.reltuples AS row_estimate
                                      , pg_total_relation_size(c.oid) AS total_bytes
                                      , pg_indexes_size(c.oid) AS index_bytes
                                      , pg_total_relation_size(reltoastrelid) AS toast_bytes
                                  FROM pg_class c
                                  LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
                                  WHERE relkind = 'r'
                          ) a
                        ) a;""")
    df = df[['table_schema','table_name','row_estimate','total_bytes','index_bytes']].sort_values('row_estimate',ascending=False)
    df = df[df['table_schema']=='public']
    df['total_bytes']=df['total_bytes']/10**9
    df['index_bytes']=df['index_bytes']/10**9
    df['row_estimate'] = (df['row_estimate']/1000).astype(int)
    df.columns = ['schema','table','mln_rows','total_Gb','index_Gb']

    if   partitions== 'no' : df = df[~df['table'].apply(lambda x: True in [xx.isdigit() for xx in x])]
    elif partitions== 'yes': df = df[ df['table'].apply(lambda x: True in [xx.isdigit() for xx in x])]
    else:                  df = df
    return df.sort_values('index_Gb',ascending=False)

# %% ../00_psql.ipynb 6
def dtypes(engine,table,schema='public'):
    return query(f"""SELECT
                    column_name,
                    data_type,
                    character_maximum_length AS max_length,
                    character_octet_length AS octet_length
                FROM
                    information_schema.columns
                WHERE
                    table_schema = '{schema}' AND 
                    table_name = '{table}';""",engine)

# %% ../00_psql.ipynb 7
query = lambda q,engine: pd.read_sql_query(q,engine)

# %% ../00_psql.ipynb 8
def current(engine):
    return query("SELECT * FROM pg_stat_activity where state = 'active';",engine)[['pid','query_start','state_change','wait_event_type','wait_event','query','backend_type']]

# %% ../00_psql.ipynb 9
def kill(pid):
    return engine.execute(f'SELECT pg_terminate_backend({pid})')

# %% ../00_psql.ipynb 10
schema = 'food'
LocalBase = declarative_base(metadata=MetaData(schema=schema))

# %% ../00_psql.ipynb 11
def insert_on_conflict(df,table,engine,update = False, update_cols = None,unique_cols=[],schema=schema):
    metadata = MetaData(schema=schema)
    metadata.bind = engine
    table = Table(table, metadata, autoload=True)
    primary_keys = [key.name for key in inspect(table).primary_key]
#     unique_cols = [cc.name for c in list(inspect(table).constraints) for cc in c if type(c) == UniqueConstraint]

    insrt_vals = df.to_dict(orient='records')
    insrt_stmnt = insert(table).values(insrt_vals)

    if update    : 
        assert update_cols, 'update_cols must be provided if update'
        set_ = {c:getattr(insrt_stmnt.excluded, c) for c in update_cols}
        do_nothing_stmt  = insrt_stmnt.on_conflict_do_update (index_elements=unique_cols,set_=set_)

    else: do_nothing_stmt  = insrt_stmnt.on_conflict_do_nothing(index_elements=unique_cols)

    engine.execute(do_nothing_stmt)

# %% ../00_psql.ipynb 12
def read_sql(table,schema,engine): return pd.read_sql(f'select * from {schema}.{table}',engine)
