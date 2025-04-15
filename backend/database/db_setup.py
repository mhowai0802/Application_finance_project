import mysql.connector
from mysql.connector import Error
import config


def create_database():
    """Create the database if it doesn't exist"""
    conn = None
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )

        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config.DB_NAME}")
            print(f"Database '{config.DB_NAME}' created or already exists")
    except Error as e:
        print(f"Error: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def create_tables():
    """Create all required tables using schema defined in config"""
    conn = None
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )

        if conn.is_connected():
            cursor = conn.cursor()

            # Create tables based on schema in config
            for table_name, schema in config.DB_SCHEMA.items():
                cursor.execute(schema)
                print(f"Table '{table_name}' created or already exists")

    except Error as e:
        print(f"Error: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    create_database()
    create_tables()