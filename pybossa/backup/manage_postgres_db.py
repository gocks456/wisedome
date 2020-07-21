import argparse
import datetime
import logging
import subprocess
import os

import configparser
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def backup_postgres_db(host, database_name, port, user, password, dest_file):
    """
    Backup postgres db to a file.
    """
    try:
        process = subprocess.Popen(
            ['pg_dump',
             '--dbname=postgresql://{}:{}@{}:{}/{}'.format(user, password, host, port, database_name),
             '-Fc',
             '-f', dest_file],
             stdout=subprocess.PIPE
        )
        output = process.communicate()[0]
        if process.returncode != 0:
            print('Command failed. Return code : {}'.format(process.returncode))
            exit(1)
        return output
    except Exception as e:
        print(e)
        exit(1)


def restore_postgres_db(db_host, db, port, user, password, backup_file):
    """Restore postgres db from a file."""
    try:
        subprocess_params = [
            'pg_restore',
            '--no-owner',
            '--dbname=postgresql://{}:{}@{}:{}/{}'.format(user,
                                                          password,
                                                          db_host,
                                                          port,
                                                          db)
        ]

        subprocess_params.append(backup_file)
        process = subprocess.Popen(subprocess_params, stdout=subprocess.PIPE)
        output = process.communicate()[0]

        if int(process.returncode) != 0:
            print('Command failed. Return code : {}'.format(process.returncode))

        return output
    except Exception as e:
        print("Issue with the db restore : {}".format(e))


def create_db(db_host, database, db_port, user_name, user_password):
    try:
        con = psycopg2.connect(dbname='postgres', port=db_port,
                               user=user_name, host=db_host,
                               password=user_password)
    except Exception as e:
        print(e)
        exit(1)

    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = con.cursor()
    cur.execute("CREATE DATABASE {} ;".format(database))
    cur.execute("GRANT ALL PRIVILEGES ON DATABASE {} TO {} ;".format(database, user_name))
    return database


def DB_backup_restore(action, dest_db=None, restored_filename=None):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    config = configparser.ConfigParser()
    for file in os.listdir(os.path.dirname(__file__) + "/conf/"):
        if file.endswith(".config"):
            config.read(os.path.join(os.path.dirname(__file__)+"/conf",file))

    postgres_host = config.get('postgresql', 'host')
    postgres_port = config.get('postgresql', 'port')
    postgres_db = config.get('postgresql', 'db')
    postgres_restore = "{}_restore".format(postgres_db)
    postgres_user = config.get('postgresql', 'user')
    postgres_password = config.get('postgresql', 'password')
    timestr = datetime.datetime.now().strftime('%Y-%m-%d %H %M %S')
    filename = 'backup-{}-{}.dump'.format(timestr, postgres_db)
    restore_database = "{}_restore".format(dest_db)
    local_storage_path = config.get('local_storage', 'path', fallback='./backups/')
    restore_filename = '{}{}'.format(local_storage_path, restored_filename)
    local_file_path = '{}{}'.format(local_storage_path, filename)

    if action == "backup":
        logger.info('Backing up {} database to {}'.format(postgres_db, local_file_path))
        result = backup_postgres_db(postgres_host,
                                    postgres_db,
                                    postgres_port,
                                    postgres_user,
                                    postgres_password,
                                    local_file_path)
        """
        if args.verbose:
            for line in result.splitlines():
                logger.info(line)
        """
        logger.info("Backup complete")

    elif action == "create":
        if dest_db is None:
            logger.warn("No dest_db was chosen for create. Run again with the '--dest-db'")
        tmp_database = create_db(postgres_host,
                                 restore_database,
                                 postgres_port,
                                 postgres_user,
                                 postgres_password)
        logger.info("Created temp database for restore : {}".format(tmp_database))

    elif action == "restore":
        if restored_filename is None or dest_db is None:
            logger.warn('No date was chosen for restore. Run again with the "--dest-db"'
                        ' and "--restored-filename"')
        else:
            logger.info("Restored Filename {}".format(restore_filename))
            logger.info("Restore starting")
            result = restore_postgres_db(postgres_host,
                                         restore_database,
                                         postgres_port,
                                         postgres_user,
                                         postgres_password,
                                         restore_filename)
            """
            if args.verbose:
                for line in result.splitlines():
                    logger.info(line)
            """
            logger.info("Restore complete")
            logger.info("Database restored and active.")

    elif action == "filepath":
        return local_storage_path

    else:
        logger.warn("No valid argument was given.")
