import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'empresa_buses.settings'
django.setup()

from django.db import connection
cursor = connection.cursor()

# List ALL tables in all schemas
cursor.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema') ORDER BY table_schema, table_name")
rows = cursor.fetchall()
print("=== ALL TABLES ===")
for r in rows:
    print(f"  {r[0]}.{r[1]}")

# Show columns for key tables found
for schema, table in rows:
    cursor.execute(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema='{schema}' AND table_name='{table}' ORDER BY ordinal_position")
    cols = cursor.fetchall()
    print(f"\n=== {schema}.{table} ===")
    for c in cols:
        print(f"  {c[0]:30s} {c[1]:20s} nullable={c[2]}")
