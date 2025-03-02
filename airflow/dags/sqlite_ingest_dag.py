"""
DAG for ingesting data from CSV files into a local SQLite database.

This DAG reads data from two provided CSV files, processes,
and then inserts resulting dataframe into SQLite database.

Original data obtained from 'https://www.kaggle.com/datasets/jordizar/climb-dataset'.
"""

from datetime import timedelta
import pendulum
from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.python import PythonOperator


def get_username():
    """
    Reads UNIX user's name to use for accessing /airflow directory and files.
    Usually, airflow dir located at /home/<username>/airflow/,
    which requires current username to access files using absolute path.

    N.B. Following function only works on UNIX systems.
    
    Returns:
        str: current username as string.
    """
    # importing inside a function to avoid top-level code
    import os
    import pwd

    return pwd.getpwuid(os.getuid()).pw_name

# Default arguments for the DAG
default_args = {
    'owner': 'savlino',
    'start_date': pendulum.today('UTC').add(days=0),
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

def read_tables(**kwargs):
    """
    Reads data from CSV files, pre-transforms and filter it, and returns as list.

    Function reads 'climber_df.csv' as main source file
    and 'grades_conversion_table.csv' to present grades according to 'Fontainebleau' system.
    Conversion performed in intermediate DataFrame to facilitate further operations in single table.
    
    **kwargs is necessary to make task instance accessible.
    
    Returns:
        list: Processed DataFrame with required columns as_list().
    """
    # importing inside a function to avoid top-level code
    import pandas as pd
    # reading main source file
    username = get_username()
    df = pd.read_csv(f'/home/{username}/airflow/data/climber_df.csv')
    # reading additional source file
    grade_conversion = pd.read_csv(
        f'/home/{username}/airflow/data/grades_conversion_table.csv'
    )
    # a dictionary for 'grades_*' columns conversion
    grade_dict = dict(
        zip(grade_conversion['grade_id'], grade_conversion['grade_fra'])
    )
    # converting grades in place
    df['grades_first'] = df['grades_first'].map(grade_dict)
    df['grades_last'] = df['grades_last'].map(grade_dict)
    df['grades_max'] = df['grades_max'].map(grade_dict)

    # columns to be presented in resulting DB
    df_columns = ['user_id', 'country', 'sex', 'height', 'weight', 'age',
                  'date_first', 'date_last', 'grades_count', 'grades_first',
                  'grades_last', 'grades_max']

    # returning selected columns as list
    return df[df_columns].to_records(index=False).tolist()

# ingesting filtered data to local SQLite database
def ingest_data(**kwargs):
    """
    Ingests data into local SQLite database table created in task 'create_table'.
    Insert operation ignores duplicates based on 'id' column.
    
    **kwargs is necessary to access task instance and fetch data from 'read_data' task.
    
    Returns: None
    """
    # importing inside function to avoid top-level code
    import sqlite3
    # accessing task instance to fetch list returned from 'read_data'
    ti = kwargs['ti']
    data_to_insert = ti.xcom_pull(task_ids='read_task')
    # connecting to local SQLite database
    conn = sqlite3.connect('/tmp/sqlite_default.db')
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT OR IGNORE INTO climbers_table (
            id, country, sex, height, weight, age,date_first, date_last,
            grades_count, grades_first, grades_last, grades_max
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data_to_insert)
    conn.commit()
    conn.close()

# creating tasks in context manager
with DAG(
    dag_id="data_ingestion_dag",
    default_args=default_args,
    schedule=None
) as dag:
    # creates new table to hold data
    create_table = SQLExecuteQueryOperator (
        task_id='create_table',
        conn_id='sqlite_default',
        sql='''
            CREATE TABLE IF NOT EXISTS climbers_table(
            id INTEGER PRIMARY KEY,
            country VARCHAR(5),
            sex INTEGER,
            height INTEGER,
            weight INTEGER,
            age REAL,
            date_first TEXT,
            date_last TEXT,
            grades_count INTEGER,
            grades_first VARCHAR(8),
            grades_last VARCHAR(8),
            grades_max VARCHAR(8)
        );
        '''
    )
    read_task = PythonOperator(
        task_id='read_task',
        python_callable=read_tables
    )
    ingest_task = PythonOperator(
        task_id='ingest_task',
        python_callable=ingest_data
    )


# pipelining tasks
create_table >> read_task >> ingest_task
