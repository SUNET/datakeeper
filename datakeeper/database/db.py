import os
import sqlite3
from pathlib import Path
from typing import Dict, Optional
from datakeeper.mixins.logger import LoggerMixin
from datakeeper.settings import DataKeeperSettings
# TODO: check database changes !!!!


class Database(LoggerMixin):
    def __init__(self, db_path: str, init_file_path: str=None, log_file: str = "database.log"):
        """Init

        Args:
            db_name (str, optional): database name. Defaults to "database.sqlite".
            init_file_path (str, optional): full path of init.sql location including the name. Default to init.sql
            log_file (str, optional): log file name
        """
        super().__init__(log_file)
        
        # Set db_path and init_file_path using settings or defaults.
        self.db_path = db_path if db_path else os.path.join(os.path.dirname(__file__), "database.sqlite") 
        self.init_path = init_file_path if init_file_path else os.path.join(os.path.dirname(__file__), "init.sql")
        
        self._init_db()


    def _init_db(self):
        self.init_sql = None

        with open(self.init_path, "r") as file:
            self.init_sql = "".join(file.readlines())

        if not os.path.exists(self.db_path):
            with sqlite3.connect(self.db_path) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.executescript(self.init_sql)
                    conn.commit()
                except Exception as err:
                    print(f"cant init database with init file {self.init_path} : {err}")

    def fetch_all(self):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            return cur.fetchall()

    def execute_script(self, sql_script: str):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.executescript(sql_script)
            conn.commit()
            return cur.fetchall()

    def execute_query(self, query, params=()):
        with sqlite3.connect(self.db_path) as conn:
            try:
                cur = conn.cursor()
                cur.execute(query, params)
                conn.commit()
                return cur.fetchall()
            except Exception as e:
                self.logger.error(f"Error during query execution: {e}", exc_info=True)

    def add_policy(self, sql_values):
        table_name = "policy"
        sql_query = f"""
        INSERT INTO {table_name} (id, name, policy_file, is_enabled, strategy, data_type, tags, paths, operations, triggers)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        formatted_query = sql_query.replace("?", "{}").format(
            *[repr(v) for v in sql_values]
        )
        self.logger.info(f"Execute {formatted_query}")
        self.execute_query(sql_query, sql_values)

    def remove_all(self):
        removed_policies = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = """
                select pol.id from policy as pol;
                """
                cursor.execute(query)
                rows = cursor.fetchall()

                for row in rows:
                    policy_id = row["id"]
                    self.delete_policy(policy_id=policy_id)
                    removed_policies.append(policy_id)

                self.logger.info(f"Removed {len(removed_policies)} scheduled policies")
                return removed_policies

        except Exception as e:
            self.logger.error(f"Error removing scheduled policy: {e}", "error")
            return []

    def delete_policy(self, policy_id):
        """
        Delete an policy and its schedule.

        Args:
            policy_id (str): ID of the object to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Delete the schedule first (foreign key constraint)
                cursor.execute("DELETE FROM job WHERE policy_id = ?", (policy_id,))

                # Delete the object
                cursor.execute("DELETE FROM policy WHERE id = ?", (policy_id,))

                deleted = cursor.rowcount > 0
                conn.commit()

                if deleted:
                    self.logger.info(f"Deleted policy with ID: {policy_id}")
                else:
                    self.logger.error(f"No policy found with ID: {policy_id}", "error")

                return deleted

        except Exception as e:
            self.logger.error(f"Error deleting policy: {e}", "error")
            return False

    def add_schedule(self, sql_values):
        table_name = "job"
        sql_query = f"""
        INSERT INTO {table_name} (id, policy_id, name, operation, filetypes, trigger_type, trigger_spec, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        formatted_query = sql_query.replace("?", "{}").format(
            *[repr(v) for v in sql_values]
        )
        self.logger.info(f"Execute {formatted_query}")
        self.execute_query(sql_query, sql_values)

    def update_schedule(self, policy_id, params: Dict):
        # status TEXT CHECK (status IN ('scheduled', 'running', 'success', 'failed')),
        """
        Update the schedule for an policy action.

        Args:
            policy_id (str): ID of the policy
            params (dict): {key: new_value}

        Returns:
            bool: True if update was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if the object exists
                cursor.execute("SELECT id FROM policy WHERE id = ?", (policy_id,))

                if not cursor.fetchone():
                    self.logger.error(
                        f"Cannot update schedule: policy with ID {policy_id} not found",
                        "error",
                    )
                    return False

                # Check if a schedule already exists for this object
                cursor.execute(
                    "SELECT policy_id FROM job WHERE policy_id = ?", (policy_id,)
                )

                if cursor.fetchone():
                    # Update existing schedule

                    sql_query = f"""
                    UPDATE job
                    SET 
                        {", ".join([f"{k} = ?" for k in params.keys()])},
                        last_run_time = CURRENT_TIMESTAMP
                    WHERE policy_id = ?
                    """
                    sql_values = [k for k in params.values()]
                    sql_values.append(policy_id)
                    formatted_query = sql_query.replace("?", "{}").format(
                        *[repr(v) for v in sql_values]
                    )
                    self.logger.info(f"Execute {formatted_query}")
                    cursor.execute(sql_query, sql_values)

                conn.commit()
                self.logger.info(f"Updated schedule for policy with ID: {policy_id}")
                return True

        except Exception as e:
            self.logger.error(f"Error updating schedule: {e}", "error")
            return False
