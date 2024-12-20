from pathlib import Path

import click

from .db import ApiDataService, CliDataService, CMDS
from .processors import (
    MODULE_PATH,
    ROOT_LOCATION,
    ApplyUpgrade,
    ConvertFiles,
    CopyFiles,
    LoadLatestLibrary,
    UpgradeCheck,
)

# from . import __version__


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(help="Tool to manage stuff", context_settings=CONTEXT_SETTINGS)
# @click.version_option(__version__)
@click.option(
    "-d",
    "--database",
    help="The database to use for upgrade checks",
    type=click.Choice(CMDS.keys()),
    default="physical",
)
@click.pass_context
def cli(ctx, database):
    ctx.ensure_object(dict)
    ctx.obj["DB_NAME"] = database


@cli.command(name="load-itunes")
@click.pass_context
def load(ctx):
    click.echo("Loading latest library data...")
    sp = MODULE_PATH / ".." / "scripts" / "load_all.applescript"
    dp = Path(f"{ROOT_LOCATION}/libraryFiles.csv").expanduser()
    l = LoadLatestLibrary(sp, dp)
    l.run()


@cli.command(name="check-upgrade")
@click.pass_context
def check(ctx):
    click.echo("Checking upgrade ...")
    db_name = ctx.obj["DB_NAME"]
    p = Path(f"{ROOT_LOCATION}/libraryFiles.csv").expanduser()
    u = UpgradeCheck(p, ApiDataService(db_name))
    u.run()


@cli.command(name="copy-files")
@click.option("-f", "--file", "_file", help="The file to process")
@click.pass_context
def copy_files(ctx, _file):
    click.echo("Copying files ...")
    db_name = ctx.obj["DB_NAME"]
    p = Path(f"{ROOT_LOCATION}/{_file}").expanduser()
    u = CopyFiles(p, CliDataService(db_name))
    u.run()


@cli.command(name="convert-files")
@click.option("-f", "--file", "_file", help="The file to process")
@click.pass_context
def convert_files(ctx, _file):
    click.echo("Converting files ...")
    db_name = ctx.obj["DB_NAME"]
    p = Path(f"{ROOT_LOCATION}/{_file}").expanduser()
    u = ConvertFiles(p, CliDataService(db_name))
    u.run()


@cli.command(name="apply-updates")
@click.option("-f", "--file", "_file", help="The file to process")
@click.pass_context
def replace_files(ctx, _file):
    click.echo("Replacing files ...")
    p = Path(f"{ROOT_LOCATION}/{_file}").expanduser()
    a = ApplyUpgrade(p)
    a.run()
