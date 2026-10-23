"""Copy a ControlCred SQLite database into an empty PostgreSQL database.

Set DATABASE_URL to the target PostgreSQL URL before running this script.
The source SQLite file is opened read-only. The destination must be empty.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path


def parse_value(value, column_type):
    if value is None:
        return None
    type_name = column_type.__class__.__name__.lower()
    if type_name == 'datetime':
        return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if type_name == 'date':
        return value if isinstance(value, date) else date.fromisoformat(str(value))
    if type_name == 'time':
        return value if isinstance(value, time) else time.fromisoformat(str(value))
    if type_name == 'boolean':
        return bool(int(value)) if isinstance(value, (int, str)) else bool(value)
    if type_name == 'numeric':
        return Decimal(str(value))
    if type_name in {'integer', 'smallinteger', 'biginteger'}:
        return int(value)
    if type_name in {'float', 'real'}:
        return float(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sqlite_file', type=Path, help='Caminho para controlcred.db')
    parser.add_argument('--target-url', default=os.getenv('DATABASE_URL'), help='URL PostgreSQL de destino')
    args = parser.parse_args()
    if not args.sqlite_file.is_file():
        parser.error(f'Banco SQLite não encontrado: {args.sqlite_file}')
    if not args.target_url:
        parser.error('Informe --target-url ou defina DATABASE_URL.')
    if args.target_url.startswith('sqlite:'):
        parser.error('O destino precisa ser PostgreSQL.')

    os.environ['AUTO_INIT_DB'] = '0'
    os.environ['DATABASE_URL'] = args.target_url
    from sqlalchemy import inspect, insert, text
    from app import app, db

    source = sqlite3.connect(f'file:{args.sqlite_file.resolve()}?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    try:
        with app.app_context():
            engine = db.engine
            source_tables = {
                row['name'] for row in source.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            db.create_all()
            with engine.begin() as connection:
                inspector = inspect(connection)
                for table in db.metadata.sorted_tables:
                    if table.name in inspector.get_table_names():
                        existing = connection.execute(
                            text(f'SELECT COUNT(*) FROM "{table.name}"')
                        ).scalar_one()
                        if existing:
                            raise RuntimeError(f"A tabela de destino '{table.name}' já contém dados; use um banco PostgreSQL vazio.")

                totals = {}
                for table in db.metadata.sorted_tables:
                    if table.name not in source_tables:
                        continue
                    source_columns = {row['name'] for row in source.execute(f'PRAGMA table_info("{table.name}")')}
                    columns = [column for column in table.columns if column.name in source_columns]
                    if not columns:
                        continue
                    selected = ', '.join('"' + column.name.replace('"', '""') + '"' for column in columns)
                    cursor = source.execute(f'SELECT {selected} FROM "{table.name}"')
                    copied = 0
                    while True:
                        batch = cursor.fetchmany(250)
                        if not batch:
                            break
                        values = [
                            {column.name: parse_value(row[column.name], column.type) for column in columns}
                            for row in batch
                        ]
                        connection.execute(insert(table), values)
                        copied += len(values)
                    totals[table.name] = copied

                if engine.dialect.name == 'postgresql':
                    for table in db.metadata.sorted_tables:
                        for column in table.primary_key.columns:
                            if not column.autoincrement:
                                continue
                            quoted_table = connection.dialect.identifier_preparer.quote(table.name)
                            quoted_column = connection.dialect.identifier_preparer.quote(column.name)
                            connection.execute(text(
                                f"SELECT setval(pg_get_serial_sequence('{table.name}', '{column.name}'), "
                                f"GREATEST(COALESCE((SELECT MAX({quoted_column}) FROM {quoted_table}), 1), 1), "
                                f"EXISTS (SELECT 1 FROM {quoted_table}))"
                            ))
            print('Migração concluída. Registros copiados por tabela:')
            for name, count in totals.items():
                print(f'  {name}: {count}')
            print('Os arquivos da pasta uploads devem ser enviados separadamente ao bucket configurado.')
            return 0
    finally:
        source.close()


if __name__ == '__main__':
    raise SystemExit(main())
