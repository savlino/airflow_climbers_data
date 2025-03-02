"""
Unit tests for validating the DAGs in Airflow project.

Module contains tests checking loading errors and task dependencies.
"""

from airflow.models import DagBag


def test_dag_loading():
    '''
    Testing if DAGs were loaded with no errors.
    '''
    dag_bag = DagBag()
    assert len(dag_bag.import_errors) == 0, 'No DAG loading errors'

def test_ingest_dependencies():
    '''
    Test validates upstream and downstream dependencies inside data_ingestion_dag.
    '''
    dag = DagBag().get_dag('data_ingestion_dag')
    tasks = dag.tasks
    dependencies = {
        'create_table': {
            'downstream': ['read_task'],
            'upstream': []
        },
        'read_task': {
            'downstream': ['ingest_task'],
            'upstream': ['create_table']
        },
        'ingest_task': {
            'downstream': [],
            'upstream': ['read_task']
        }
    }
    for task in tasks:
        print(task)
        assert task.downstream_task_ids == set(
            dependencies[task.task_id]['downstream']
        )
        assert task.upstream_task_ids == set(
            dependencies[task.task_id]['upstream']
        )

def test_transform_dependencies():
    '''
    Test validates upstream and downstream dependencies inside data_transform_dag.
    '''
    dag = DagBag().get_dag('data_transform_dag')
    tasks = dag.tasks
    dependencies = {
        'create_new_table': {
            'downstream': ['transform_sex_to_char'],
            'upstream': []
        },
        'transform_sex_to_char': {
            'downstream': ['trim_time_from_date_col'],
            'upstream': ['create_new_table']
        },
        'trim_time_from_date_col': {
            'downstream': ['transform_to_new_table'],
            'upstream': ['transform_sex_to_char']
        },
        'transform_to_new_table': {
            'downstream': ['drop_source_table'],
            'upstream': ['trim_time_from_date_col']
        },
        'drop_source_table': {
            'downstream': [],
            'upstream': ['transform_to_new_table']
        }
    }
    for task in tasks:
        print(task)
        assert task.downstream_task_ids == set(
            dependencies[task.task_id]['downstream']
        )
        assert task.upstream_task_ids == set(
            dependencies[task.task_id]['upstream']
        )
