from dagster import (
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    load_assets_from_package_module,
)

from . import assets

daily_refresh_schedule = ScheduleDefinition(
    job=define_asset_job(name="all_assets_job"), cron_schedule="0 0 * * *"
)

defs = Definitions(
    assets=load_assets_from_package_module(assets), schedules=[daily_refresh_schedule]
)

# R2AE
from dagster_fivetran import FivetranResource, load_assets_from_fivetran_instance
from dagster import EnvVar

# Pull API key and secret from environment variables
fivetran_instance = FivetranResource(
    api_key=EnvVar("FIVETRAN_API_KEY"),
    api_secret=EnvVar("FIVETRAN_API_SECRET")
)

fivetran_assets = load_assets_from_fivetran_instance(fivetran_instance)