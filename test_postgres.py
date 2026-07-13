import psycopg

try:
    conn = psycopg.connect(
        dbname="empresa_buses",
        user="postgres",
        password="pass1234",
        host="localhost",
        port="5432"
    )

    print("CONEXIÓN OK")

except Exception as e:
    print(type(e))
    print(e)