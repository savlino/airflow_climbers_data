"""
DAG for transforming data previously ingested in local SQLite database table.

This DAG creates a new table in the SQLite database and transfers modified data from existing table.
"""

from datetime import timedelta
import pendulum
from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator


# Default arguments for the DAG
default_args = {
    'owner': 'savlino',
    'start_date': pendulum.today('UTC').add(days=0),
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

# creating DAGs in context manager
with DAG(
    dag_id="data_transform_dag",
    default_args=default_args,
    schedule=None
) as dag:
    # task creates new table for transformed data
    # since SQLite not allows alter data formats for columns
    create_new_table = SQLExecuteQueryOperator (
        task_id='create_new_table',
        conn_id='sqlite_default',
        sql='''
            CREATE TABLE IF NOT EXISTS climbers_transformed(
            id INTEGER PRIMARY KEY,
            country VARCHAR(5),
            sex VARCHAR(1),
            height INTEGER,
            weight INTEGER,
            age INTEGER,
            date_first TEXT,
            date_last TEXT,
            grades_count INTEGER,
            grades_first VARCHAR(8),
            grades_last VARCHAR(8),
            grades_max VARCHAR(8)
        );
        '''
    )
    # 'sex' value present in source table as binary integer value
    # this task converts them to single char value
    # 'M' stands for men atheletes, 'F' for women atheletes
    transform_sex_to_char = SQLExecuteQueryOperator(
        task_id='transform_sex_to_char',
        conn_id='sqlite_default',
        sql='''
            UPDATE climbers_table
            SET sex = CASE
                WHEN sex = 0 THEN 'M'
                WHEN sex = 1 THEN 'F'
                ELSE sex
            END;
        '''
    )
    # 'date_first' and 'date_last' columns formatted as 'yyyy-mm-dd hh:mm:ss'
    # following task saves first 10 characters to present date only
    trim_time_from_date_col = SQLExecuteQueryOperator(
        task_id='trim_time_from_date_col',
        conn_id='sqlite_default',
        sql='''
            UPDATE climbers_table
            SET
                date_first = substr(date_first, 1, 10),
                date_last = substr(date_last, 1, 10);
        '''
    )
    # transformed values inserted into temporary table
    # casting 'age' as integer value
    transform_to_new_table = SQLExecuteQueryOperator(
        task_id='transform_to_new_table',
        conn_id='sqlite_default',
        sql='''
            INSERT INTO climbers_transformed(
                id, country, sex, height, weight, age,date_first, date_last,
                grades_count, grades_first, grades_last, grades_max
            )
            SELECT id, country, sex, height, weight,
                CAST (age AS INTEGER),
                date_first, date_last,
                grades_count,
                grades_first, grades_last, grades_max
            FROM climbers_table;
        '''
    )
    # dropping source table after successful transfer
    drop_source_table = SQLExecuteQueryOperator(
        task_id='drop_source_table',
        conn_id='sqlite_default',
        sql='''
            DROP TABLE climbers_table;
        '''
    )


# pipelining tasks
create_new_table >> transform_sex_to_char >> trim_time_from_date_col >> \
transform_to_new_table >> drop_source_table
