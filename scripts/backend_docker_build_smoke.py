#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_docker_build_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/10 10:33
# @Description : Run the SkyRadar backend Docker build smoke command.

"""Run the SkyRadar backend Docker build smoke command."""

from loguru import logger
import argparse
import shlex
import subprocess
import sys



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


DEFAULT_TAG = "skyradar-backend-build-smoke"
DEFAULT_CONTEXT = "."


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build the SkyRadar backend Docker image as a smoke check. "
            "This script only runs docker build; it does not start a container "
            "or perform HTTP smoke checks."
        )
    )
    parser.add_argument(
        "--platform",
        help="Optional Docker target platform, for example linux/amd64 or linux/arm64.",
    )
    parser.add_argument(
        "--tag",
        default=DEFAULT_TAG,
        help="Docker image tag, default: %(default)s",
    )
    parser.add_argument(
        "--context",
        default=DEFAULT_CONTEXT,
        help="Docker build context, default: %(default)s",
    )
    parser.add_argument(
        "--dockerfile",
        help="Optional Dockerfile path passed as docker build -f.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the docker build command without executing it.",
    )
    return parser.parse_args()


def build_command(args):
    command = [
        "docker",
        "build",
        "-t",
        args.tag,
    ]
    if args.platform:
        command[2:2] = ["--platform", args.platform]
    if args.dockerfile:
        command.extend(["-f", args.dockerfile])
    command.append(args.context)
    return command


def main():
    configure_logging()
    args = parse_args()
    command = build_command(args)

    if args.dry_run:
        logger.info(shlex.join(command))
        return 0

    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
