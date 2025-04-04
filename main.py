import os
import sys
import click
from pathlib import Path
from datakeeper.database.db import Database
from datakeeper.policy_store import PolicyStore
from datakeeper.job_scheduler import JobScheduler
from datakeeper.settings import DataKeeperSettings
from datakeeper.policy_manager import PolicyManager
from datakeeper.data_generator import DataGenerator
from importlib.metadata import PackageNotFoundError, version as importlib_version

@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show the version of datakeeper.")
def cli(version):
    """CLI tool for syncing and listing devices."""
    if version:
        try:
            package_version = importlib_version("datakeeper")
            click.echo(f"datakeeper:{package_version}")
        except PackageNotFoundError:
            try:
                base_path = getattr(sys, '_MEIPASS', os.path.dirname(__file__))  # Handle PyInstaller path
                version_file = os.path.join(base_path, "VERSION")
                with open(version_file, "r") as f:
                    package_version = f.read().strip()
                click.echo(f"datakeeper:{package_version}")
            except FileNotFoundError:
                click.echo("Version file not found.")
            #click.echo("Package datakeeper is not installed.")


@click.command()
#@click.option("--temp", required=False, default=None, help="User name for NI.")
@click.option(
    "--config",
    required=False,
    type=click.Path(exists=True),
    help="Path to the configuration file.",
)
@click.option(
    "--verbose", is_flag=True, required=False, help="Enable verbose output."
)
def schedule(config, verbose):
    """
    Schedule monotoring jobs for data retention policy
    """
    settings = DataKeeperSettings(config)
    print(settings)
    datastore_db = Database(db_path=settings.db_path, init_file_path=settings.init_file_path)

    # Initialize the policy store
    policy_store = PolicyStore(
        db=datastore_db,
        policy_path=settings.policy_path,
        plugin_dir=settings.plugin_dir
    )
    
    # Initialize the job scheduler
    job_scheduler = JobScheduler(
        db=datastore_db,
        policy_store=policy_store,
    )

    policy_mgmt = PolicyManager(
        policy_store=policy_store, job_scheduler=job_scheduler, database=datastore_db
    )
    # policy_mgmt.start_simple()
    policy_mgmt.start()
    
    
@click.command()
@click.option("--base-dir", required=False, default=None, help="Base directory for storing generated files.")
@click.option("--random-age", is_flag=True, required=False, help="Generate files with random ages.")
@click.option("--num-files", required=False, default=5, type=int, help="Number of files to generate.")
@click.option("--create-dir", is_flag=True, required=False, help="Create the base directory if it does not exist.")
@click.option(
    "--format",
    type=click.Choice(["csv", "hdf5"]),
    required=True,
    show_default=True,
    help="Specify the output file format ('csv' or 'hdf5').",
)
@click.option("--sub-dir", required=False, default=None, help="Subdirectory within the base directory.")
def generate(base_dir, random_age, num_files, create_dir, format, sub_dir):
    """
    Generate data files according to specified options.
    """

    data_generator = DataGenerator(
        base_directory=base_dir,
        random_age=random_age,
        number_of_files=num_files,
        create_dir=create_dir,
    )
    data_generator.generate(subdirectory=sub_dir, format=format)

        
cli.add_command(schedule)
cli.add_command(generate)

if __name__ == "__main__":
    # sys.exit(cli())
    cli()