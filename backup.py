import pymysql

# Set connection parameters
connection = pymysql.connect(
    host='udesh.mysql.pythonanywhere-services.com',
    user='udesh',
    password='Iratusbison@123',  # Replace with actual password
    database='udesh$gym'
)

# Open a file to write backup data
with open('/home/udesh/my_table_backup.sql', 'w') as f:
    cursor = connection.cursor()

    # Get a list of tables
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    for table in tables:
        f.write(f"-- Backup of table: {table[0]}\n")
        # Export the structure (CREATE TABLE)
        cursor.execute(f"SHOW CREATE TABLE {table[0]}")
        create_table = cursor.fetchone()
        f.write(f"{create_table[1]};\n")

        # Export the data (INSERT INTO)
        cursor.execute(f"SELECT * FROM {table[0]}")
        rows = cursor.fetchall()
        for row in rows:
            row_values = ', '.join([f"'{value}'" for value in row])
            f.write(f"INSERT INTO {table[0]} VALUES ({row_values});\n")

# Close the connection
connection.close()
