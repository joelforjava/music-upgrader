from pathlib import Path
import click

# from . import __version__
# from .connect import clients

from .db import ApiDataService, CliDataService
from .processors import CopyFilesForUpgrade, UpgradeCheck, ROOT_LOCATION


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(help="Tool to manage stuff", context_settings=CONTEXT_SETTINGS)
# @click.version_option(__version__)
@click.option("-d", "--database", help="The database to use for upgrade checks", default="physical")
@click.pass_context
def cli(ctx, database):
    ctx.ensure_object(dict)
    ctx.obj["DB_NAME"] = database


@cli.command(name="check-upgrade")
@click.pass_context
def check(ctx):
    click.echo("Checking upgrade ...")
    db_name = ctx.obj["DB_NAME"]
    u = UpgradeCheck(ApiDataService(db_name))
    u.run(Path(f"{ROOT_LOCATION}/libraryFiles.csv").expanduser())


@cli.command(name="copy-files")
@click.option("-f", "--file", "_file", help="The file to process")
@click.pass_context
def copy_files(ctx, _file):
    click.echo("Copying files ...")
    db_name = ctx.obj["DB_NAME"]
    u = CopyFilesForUpgrade(CliDataService(db_name))
    u.run(Path(f"{ROOT_LOCATION}/{_file}").expanduser())
