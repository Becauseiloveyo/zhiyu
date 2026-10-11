"""Local administration only; no remote activation or device operations."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from zhiyu.core.errors import DomainError
from zhiyu.db.session import get_sessionmaker
from zhiyu.repositories.audit import AuditRepository
from zhiyu.services.bootstrap import BootstrapBundle, BootstrapService


def main() -> int:
    parser = argparse.ArgumentParser(prog="zhiyu")
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser("bootstrap")
    bootstrap.add_argument("--file", type=Path, required=True)
    bootstrap.add_argument("--actor", required=True)
    audit = commands.add_parser("verify-audit")
    audit.add_argument("--environment", required=True)
    args = parser.parse_args()
    try:
        with get_sessionmaker()() as db:
            if args.command == "bootstrap":
                bundle = BootstrapBundle.model_validate_json(args.file.read_text(encoding="utf-8"))
                print(json.dumps(BootstrapService(db).apply(bundle, actor_id=args.actor)))
            else:
                with db.begin():
                    valid = AuditRepository(db).verify_chain(args.environment)
                print(json.dumps({"audit_chain_valid": valid}))
                return 0 if valid else 1
    except (SQLAlchemyError, DomainError, ValidationError, OSError) as error:
        print(json.dumps({"status": "error", "error_class": type(error).__name__}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
