from sqlalchemy import inspect, text


def auto_migrate_columns(engine, base):
    """
    يقارن أعمدة كل موديل بايثون مع أعمدة قاعدة البيانات الحقيقية.
    أي عمود موجود بالموديل وناقص بقاعدة البيانات، يُضاف تلقائيًا (ALTER TABLE).
    يشتغل عند كل تشغيل للسيرفر — بلا حاجة لأي ملف يدوي مستقبلًا.
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    type_map = {
        "INTEGER": "INTEGER",
        "VARCHAR": "VARCHAR",
        "FLOAT": "FLOAT",
        "BOOLEAN": "BOOLEAN",
        "DATETIME": "TIMESTAMP",
        "JSON": "JSON",
        "TEXT": "TEXT",
    }

    with engine.connect() as conn:
        for table_name, table in base.metadata.tables.items():
            if table_name not in existing_tables:
                continue  # جدول جديد بالكامل — create_all يتكفل بيه لحاله
            existing_columns = {c["name"] for c in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                col_type = str(column.type).split("(")[0].upper()
                sql_type = type_map.get(col_type, "VARCHAR")

                default_clause = ""
                if column.default is not None and getattr(column.default, "is_scalar", False):
                    val = column.default.arg
                    if isinstance(val, str):
                        default_clause = f" DEFAULT '{val}'"
                    elif isinstance(val, bool):
                        default_clause = f" DEFAULT {str(val).upper()}"
                    elif isinstance(val, (int, float)):
                        default_clause = f" DEFAULT {val}"

                stmt = f'ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS "{column.name}" {sql_type}{default_clause};'
                print(f"[auto-migrate] {stmt}")
                conn.execute(text(stmt))

            model_columns = {c.name for c in table.columns}
            for db_col in inspector.get_columns(table_name):
                if db_col["name"] in model_columns:
                    continue
                if not db_col.get("nullable", True):
                    stmt = f'ALTER TABLE {table_name} ALTER COLUMN "{db_col["name"]}" DROP NOT NULL;'
                    print(f"[auto-migrate] {stmt}")
                    conn.execute(text(stmt))
        conn.commit()
