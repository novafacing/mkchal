"""Helper for quickly boilerplating CTF challenges."""

import argparse
import string
from dataclasses import dataclass
from enum import Enum
from json import dumps
from pathlib import Path
from typing import List, Optional

import git


class Type(str, Enum):
    """Describes a CTF challenge type."""

    REV = "rev"
    PWN = "pwn"
    CRYPTO = "crypto"
    WEB = "web"
    MISC = "misc"


class DeployType(str, Enum):
    """Describes a deployment type."""

    DOCKER_COMPOSE = "docker-compose"


@dataclass
class Challenge:
    """Represents a CTF challenge."""

    type: Type
    name: str
    author: str
    description: str
    difficulty: str
    flag: str
    provides: List[str]
    ports: List[int]
    remote: Optional[List[str]]
    target: Optional[str]


def get_repo(path: Optional[Path] = None) -> Path:
    """
    Returns the top-level repository directory.

    :param path: Optionally, the provided path to search in.
        Defaults to CWD.
    :returns: A path to the directory containing `.git`.
    """
    if path is None:
        path = Path.cwd()

    repo = git.Repo(path, search_parent_directories=True)
    return Path(repo.working_dir)


def create_challenge(challenge: Challenge) -> None:
    """
    Creates a new challenge.

    :param challenge: The challenge to create.
    """
    if challenge.target is None:
        cld = get_repo() / challenge.type.value
    else:
        cld = Path(challenge.target)

    if not cld.exists():
        cld.mkdir(parents=True)

    chal_dir = cld / challenge.name

    if not chal_dir.exists():
        chal_dir.mkdir()

    with (chal_dir / "chal.json").open("w") as chal_desc:
        chal_desc.write(dumps(challenge.__dict__, indent=4, sort_keys=True))

    if challenge.remote is not None:
        (chal_dir / "deploy").mkdir()
        with (chal_dir / "deploy.sh").open("w") as deploy_file:
            deploy_file.write(f"#!/bin/bash\n{' '.join(challenge.remote)}")
        templates_to_write = {}
        for template in (Path(__file__).with_name("templates") / "deploy").iterdir():
            with template.open("r") as template_file:
                templates_to_write[template.name] = template_file.read()

        all_formatters = {
            "name": challenge.name,
            "dist_path": str(chal_dir / "dist"),
            "port": str(challenge.ports[0]),
        }
        for template_name, template_content in templates_to_write.items():
            with (chal_dir / "deploy" / template_name).open("w") as template_target:

                formatters = {
                    t[1]: all_formatters[t[1]]
                    for t in string.Formatter().parse(template_content)
                    if t[1] is not None
                }
                template_target.write(template_content.format(**formatters))

    (chal_dir / "solve").mkdir()

    with (chal_dir / "solve" / "flag.txt").open("w") as flag_file:
        flag_file.write(challenge.flag)

    (chal_dir / "src").mkdir()

    with (chal_dir / "src" / "Makefile").open("w") as make_file:
        make_file.write(
            "CC=\n"
            "CXX=\n"
            "CFLAGS=\n"
            "CXXFLAGS=\n"
            "LDFLAGS=\n"
            "\n"
            f"all: {challenge.name}\n"
            "\n"
            f"{challenge.name}: {challenge.name}.c\n"
            "\t$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^\n"
        )

    (chal_dir / "dist").mkdir()


def main() -> None:
    """Main CLI entrypoint to mkchal"""
    parser = argparse.ArgumentParser(
        prog="mkchal", description="Create a CTF challenge."
    )
    parser.add_argument(
        "--type",
        "-t",
        type=Type,
        required=True,
        choices=[c.value for c in Type],
        help="The type of the challenge.",
    )
    parser.add_argument(
        "--name",
        "-n",
        type=str,
        required=True,
        help="The name of the challenge. Example: `a_creative_name`",
    )
    parser.add_argument(
        "--author",
        "-a",
        type=str,
        required=True,
        help="The author's name. Example: `you`",
    )
    parser.add_argument(
        "--description",
        "-d",
        nargs="+",
        type=str,
        required=True,
        help="The description of the challenge. Example: `This is a description...good luck!",
    )
    parser.add_argument(
        "--difficulty",
        "-D",
        choices=["Easy", "Medium", "Hard"],
        required=True,
        help="The difficulty level of the challenge.",
    )
    parser.add_argument(
        "--flag",
        "-f",
        type=str,
        required=True,
        help="The flag for the challenge. Example: `flag{flag!}`",
    )
    parser.add_argument(
        "--provides",
        "-p",
        nargs="+",
        type=Path,
        required=True,
        help=(
            "The paths to files that the challenge provides. "
            "Example: `dist/chal dist/chal.tar.gz`"
        ),
    )
    parser.add_argument(
        "--ports",
        "-P",
        nargs="+",
        type=int,
        required=True,
        help="The ports that the challenge provides. Example: 1337 1338",
    )
    parser.add_argument(
        "--remote",
        "-r",
        nargs="+",
        type=str,
        required=False,
        default=None,
        help=(
            "The command to run from the challenge directory to deploy."
            "Example: `docker-compose --project_name chal up --build`"
        ),
    )
    parser.add_argument(
        "--target",
        "-T",
        type=str,
        required=False,
        default=None,
        help=(
            "An optional target directory to create the challenge in. "
            "If not specified, uses ./category/name"
        ),
    )
    args = parser.parse_args()

    chal = Challenge(
        type=args.type,
        name=args.name,
        author=args.author,
        description=" ".join(args.description),
        difficulty=args.difficulty,
        flag=args.flag,
        provides=list(map(str, args.provides)),
        ports=args.ports,
        remote=args.remote,
        target=args.target,
    )

    create_challenge(chal)
    print(
        f"Done. Run `git checkout -b {args.type}_{args.name}` to switch "
        "to a branch and start working."
    )


if __name__ == "__main__":
    main()
