import sqlite3
import os

def fix_db():
    print("Dumping and fixing database schema...")
    conn = sqlite3.connect('database.db')
    
    # Dump the database and replace the buggy table name
    with open('dump.sql', 'w', encoding='utf-8') as f:
        for line in conn.iterdump():
            f.write(line.replace('"services_old_temp"', 'services') + '\n')
    conn.close()
    
    # Remove the old database
    os.remove('database.db')
    
    # Recreate the database with the fixed schema
    print("Recreating database...")
    conn = sqlite3.connect('database.db')
    with open('dump.sql', 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.close()
    
    # Clean up
    os.remove('dump.sql')
    print("Database fixed successfully! You can now run your app.")

if __name__ == '__main__':
    fix_db()