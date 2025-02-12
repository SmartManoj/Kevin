# simple sqlite db to store user_id and port number

import sqlite3

def create_db():
    conn = sqlite3.connect('port_db.sqlite')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS ports (user_id TEXT PRIMARY KEY, port INTEGER)')
    conn.commit()
    return conn

def get_port(user_id):
    conn = create_db()
    c = conn.cursor()
    c.execute('SELECT port FROM ports WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def store_port(user_id, port):
    try:
        conn = create_db()
        c = conn.cursor()
        c.execute('INSERT INTO ports(user_id, port) VALUES (?, ?)', (user_id, port))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error storing port: {e}")


if __name__ == '__main__':
    # store_port('123', 1234)
    print(get_port('123'))

