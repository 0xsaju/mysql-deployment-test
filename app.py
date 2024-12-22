from flask import Flask, jsonify
import mysql.connector
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
    except mysql.connector.Error as err:
        logger.error(f"Database connection failed: {err}")
        raise

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "version": "1.0.1"  # Added version number
    }), 200

@app.route('/init-db')
def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create a test table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message VARCHAR(255)
            )
        ''')
        
        # Insert a test record
        cursor.execute('INSERT INTO test_table (message) VALUES (%s)', ('Test message',))
        conn.commit()
        
        # Read the inserted record
        cursor.execute('SELECT * FROM test_table ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Database initialized and tested",
            "data": {
                "id": result[0],
                "message": result[1]
            }
        }), 200
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/check-db')
def check_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Test table existence
        cursor.execute("SHOW TABLES LIKE 'test_table'")
        table_exists = cursor.fetchone() is not None
        
        # Test data if table exists
        data = None
        if table_exists:
            cursor.execute('SELECT * FROM test_table LIMIT 1')
            result = cursor.fetchone()
            if result:
                data = {"id": result[0], "message": result[1]}
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Database connection successful",
            "details": {
                "table_exists": table_exists,
                "has_data": data is not None,
                "sample_data": data
            }
        }), 200
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
