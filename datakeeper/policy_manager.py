import os
import time
import logging
import threading
from datakeeper.database.db import Database
from datakeeper.policy_store import PolicyStore
from datakeeper.mixins.logger import LoggerMixin
from datakeeper.job_scheduler import JobScheduler


class PolicyManager(LoggerMixin):
    def __init__(
        self, policy_store, job_scheduler, database, log_file="policy_mgmt_system.log"
    ):
        super().__init__(log_file)
        """Main entry point for the application."""

        # Initialize
        self.policy_store: PolicyStore = policy_store
        self.job_scheduler: JobScheduler = job_scheduler
        self.database: Database = database

    def monitor_policy_changes(self, policy_store, job_scheduler, check_interval=300):
        """Monitor for changes to policy files and reload when necessary."""
        logger = logging.getLogger("PolicyMonitor")
        last_modified = (
            os.path.getmtime(policy_store.policy_path)
            if os.path.exists(policy_store.policy_path)
            else 0
        )

        while not job_scheduler._stop_event.is_set():
            try:
                if os.path.exists(policy_store.policy_path):
                    current_modified = os.path.getmtime(policy_store.policy_path)
                    if current_modified > last_modified:
                        logger.info("Policy file changed, reloading policies")
                        changes = policy_store.reload()
                        logger.info(f"Policy changes: {changes}")
                        job_scheduler.reschedule_all_jobs()
                        last_modified = current_modified
            except Exception as e:
                logger.error(f"Error monitoring policy changes: {e}", exc_info=True)

            # Wait for the next check interval or until stopped
            job_scheduler._stop_event.wait(check_interval)

    def start_monitor_thread(self):
        # Start a policy file monitor in another thread
        monitor_thread = threading.Thread(
            target=self.monitor_policy_changes,
            args=(
                self.policy_store,
                self.job_scheduler,
                int(os.getenv("POLICY_CHECK_INTERVAL", 300)),
            ),
            daemon=True,
            name="PolicyMonitorThread",
        )
        monitor_thread.start()
        self.logger.info("Policy monitor started in background thread")

    def start_simple(self):
        self.logger.info("Starting Policy System")

    def start(self):
        self.logger.info("Starting Policy System")

        try:
            # Start the scheduler in a daemon thread
            self.scheduler_thread = self.job_scheduler.run_in_thread()
            self.logger.info("Job scheduler started in background thread")

            # Keep the main thread alive
            self.logger.info("Main application running. Press Ctrl+C to exit.")
            try:
                # TODO: [Call  web server &  FastAPI & main application logic]

                # This keep the main thread alive
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt, shutting down...")
            finally:
                # Shutdown the job scheduler
                self.database.remove_all()
                self.job_scheduler.shutdown()
                self.logger.info("Application shutdown complete")

        except Exception as e:
            self.logger.error(f"Error in main application: {e}", exc_info=True)
            return 1

        return 0


