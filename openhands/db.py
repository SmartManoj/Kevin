# simple sqlite db to store user_id and port number

import sqlite3

def create_db():
    conn = sqlite3.connect('port_db.sqlite')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS ports (user_id TEXT PRIMARY KEY, port INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    c.execute('CREATE TABLE IF NOT EXISTS credits (user_id TEXT PRIMARY KEY, amount INTEGER NOT NULL)')
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

def get_credits(user_id):
    conn = create_db()
    c = conn.cursor()
    c.execute('SELECT amount FROM credits WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if not result:
        c.execute('INSERT INTO credits(user_id, amount) VALUES (?, ?)', (user_id, 30))
        conn.commit()
        count = 30
    else:
        count = result[0]
    conn.close()
    return count

def set_credits(user_id, amount):
    conn = create_db()
    c = conn.cursor()
    c.execute('UPDATE credits SET amount = ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_all_credits():
    conn = create_db()
    c = conn.cursor()
    c.execute('SELECT * FROM credits')
    result = c.fetchall()
    conn.close()
    return result
if __name__ == '__main__':
    # store_port('123', 1234)
    print(get_credits('123'))
    print(get_all_credits())

