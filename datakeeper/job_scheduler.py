import sys
import time
import signal
import threading
from typing import Dict
from database.db import Database
from policy_store import PolicyStore
from mixins.logger import LoggerMixin
from policy_system.plugin_registry import Policy
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED


class JobScheduler(LoggerMixin):
    """Scheduler for policy jobs that runs in the background."""
    
    def __init__(self,  db: Database, policy_store: PolicyStore, log_file: str="policy_store.log"):
        # Set up logging
        super().__init__(log_file)
        
        self.database = db
        self.log_info("Initializing JobScheduler")
        
        self.policy_store: PolicyStore = policy_store
        
        # Use coalescing for the scheduler to prevent duplicate runs
        self.scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 60  # Allow misfires up to 60 seconds late
            }
        )
        
        # Add event listeners to monitor job execution
        self.scheduler.add_listener(
            self._job_executed_listener, 
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener, 
            EVENT_JOB_ERROR
        )
        
        # For graceful shutdown
        self._stop_event = threading.Event()
        self.job_count = 0
        
        try:
            # Register signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
        except Exception as e:
            self.log_error(f"Error during initialization: {e}", exc_info=True)
            raise
    
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals."""
        self.log_info(f"Received signal {signum}, shutting down...")
        self._stop_event.set()
        self.shutdown()
    
    def _job_executed_listener(self, event):
        """Log when jobs are successfully executed."""
        self.log_info(f"Job {event.job_id} executed successfully")
    
    def _job_error_listener(self, event):
        """Log when jobs encounter errors."""
        self.log_error(f"Job {event.job_id} encountered an error: {event.exception}", 
                        exc_info=(event.exception_type, event.exception, event.traceback))
    
    def start(self):
        """Start the scheduler."""
        try:
            self.log_info("Starting scheduler")
            self.scheduler.start()
            self.log_info("Scheduler started successfully")
            return True
        except Exception as e:
            self.log_error(f"Failed to start scheduler: {e}", exc_info=True)
            return False
    
    def setup_jobs(self):
        """Set up scheduled jobs for all policies that have schedule triggers."""
        self.log_info("Setting up scheduled jobs")
        self.job_count = 0
        
        # Get all policies with schedule triggers
        scheduled_policies = self.policy_store.get_scheduled_policies()
        self.log_info(f"job_count=>{self.job_count}")
        self.log_info(f"scheduled_policies=>{scheduled_policies}")

        for policy, trigger in scheduled_policies:
            trigger_spec = trigger.get("spec", {})
            self.log_info(f"policy=>{policy}")
            self.log_info(f"schedule_type=>{trigger_spec.get("type")}")
            self.log_info(f"trigger_spec=>{trigger_spec}")
            job_id = self._schedule_policy_execution(policy, trigger_spec)
            if job_id:
                self.job_count += 1
        
        self.log_info(f"Scheduled {self.job_count} jobs from {len(scheduled_policies)} policies")
        return self.job_count


    def _schedule_policy_execution(self, policy: Policy, trigger_spec: Dict):
        """Schedule a policy to be executed based on trigger specification."""
        schedule_type = trigger_spec.get("type")
        policy_name = policy.name
        
        try:
            # Policy executor funcion to be scheduled
            def execute_policy():
                self.log_info(f"Executing scheduled policy '{policy_name}'")
                try:
                    context = {
                        "scheduled": True, 
                        "policy_name": policy_name,
                        "policy_id": policy.uniq_id,
                        "trigger_time": time.time(),
                        "execution_id": f"exec_{int(time.time())}",
                        "database": self.database
                    }
                    result = policy.apply(context)
                    self.log_info(f"Successfully applied policy '{policy_name}'")
                    return result
                except Exception as e:
                    self.log_error(f"Error executing policy '{policy_name}': {e}", exc_info=True)
                    raise
            
            # Configure the appropriate trigger based on the schedule type
            trigger = None
            # job_id = f"policy_{policy_name}_{schedule_type}_{int(time.time())}"
            job_id = policy.uniq_id
            
            if schedule_type == "cron":
                cron_expression = trigger_spec.get("cron", "0 0 * * *")
                self.log_info(f"Setting up cron schedule '{cron_expression}' for policy '{policy_name}'")
                try:
                    trigger = CronTrigger.from_crontab(cron_expression)
                except Exception as e:
                    self.log_error(f"Invalid cron expression '{cron_expression}': {e}")
                    return None
                
            elif schedule_type == "interval":
                # Interval in minutes, hours, days, etc.
                interval_unit = trigger_spec.get("unit", "hours")
                interval_value = trigger_spec.get("value", 1)
                trigger_kwargs = {interval_unit: interval_value}
                self.log_info(f"Setting up interval schedule (every {interval_value} {interval_unit}) for policy '{policy_name}'")
                trigger = IntervalTrigger(**trigger_kwargs)
                
            elif schedule_type == "date":
                # Specific date/time
                run_date = trigger_spec.get("date")
                if not run_date:
                    self.log_error(f"No date specified for date trigger in policy '{policy_name}'")
                    return None
                self.log_info(f"Setting up one-time execution at {run_date} for policy '{policy_name}'")
                trigger = DateTrigger(run_date=run_date)
                
            else:
                self.log_error(f"Unknown schedule type: {schedule_type} for policy '{policy_name}'")
                return None
            
            # Add the job to the scheduler
            self.scheduler.add_job(
                execute_policy,
                trigger=trigger,
                id=job_id,
                name=f"Policy: {policy_name}",
                replace_existing=True
            )
            
            self.log_info(f"Scheduled policy '{policy_name}' with {schedule_type} trigger (job ID: {job_id})")
            self.database.update_schedule(
                policy_id=policy.uniq_id,
                params={
                    "status": 'scheduled'
            })
            return job_id
            
        except Exception as e:
            self.log_error(f"Error scheduling policy '{policy_name}': {e}", exc_info=True)
            return None
    
    def reschedule_all_jobs(self):
        """Remove all existing jobs and reschedule from current policies."""
        # Remove all existing jobs
        for job in self.scheduler.get_jobs():
            self.scheduler.remove_job(job.id)
        
        # Setup new jobs
        return self.setup_jobs()
    
    def run_as_daemon(self):
        """Run the scheduler as a daemon process that doesn't block the main thread."""
        self.log_info("Starting JobScheduler in daemon mode")
        
        # Start the scheduler
        if not self.start():
            self.log_error("Failed to start scheduler, exiting")
            return
        
        # Setup scheduled jobs
        self.setup_jobs()
        
        # Keep the process alive without consuming significant resources
        self.log_info("JobScheduler running in background mode")
        
        try:
            # Block until the stop event is set (which would be done by signal handlers)
            while not self._stop_event.wait(timeout=60):  # Check every minute
                # Periodic maintenance tasks -> check if scheduler is still running
                if not self.scheduler.running:
                    self.log_error("Scheduler stopped unexpectedly, attempting restart")
                    self.start()
        except Exception as e:
            self.log_error(f"Error in daemon loop: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    def run_in_thread(self):
        """Run the scheduler in a separate daemon thread."""
        thread = threading.Thread(
            target=self.run_as_daemon,
            daemon=True,
            name="JobSchedulerDaemon"
        )
        thread.start()
        return thread
    
    def shutdown(self):
        """Gracefully shut down the scheduler."""
        self.log_info("Shutting down JobScheduler...")
        if hasattr(self, 'scheduler') and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.log_info("Scheduler shut down")
        # Set the stop event to ensure any waiting loops exit
        self._stop_event.set()
        self.log_info("JobScheduler shutdown complete")
        sys.exit(0)
    
    def __del__(self):
        """Ensure the scheduler is shut down properly."""
        if hasattr(self, 'scheduler') and hasattr(self.scheduler, 'running') and self.scheduler.running:
            try:
                self.scheduler.shutdown(wait=False)
            except Exception as _:
                # Suppress errors during garbage collection
                pass
