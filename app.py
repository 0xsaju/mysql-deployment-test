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
        cursor = conn.cursor(dictionary=True)  # Return results as dictionary
        
        logger.info("Creating test_table if not exists")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message VARCHAR(255)
            )
        ''')
        
        logger.info("Inserting test record")
        cursor.execute('INSERT INTO test_table (message) VALUES (%s)', ('Test message',))
        conn.commit()
        
        logger.info("Verifying inserted record")
        cursor.execute('SELECT * FROM test_table ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            logger.info(f"Successfully created and inserted data: {result}")
            return jsonify({
                "status": "success",
                "message": "Database initialized and tested",
                "data": result
            }), 200
        else:
            logger.error("No data returned after insert")
            return jsonify({
                "status": "error",
                "message": "Failed to verify inserted data"
            }), 500
            
    except mysql.connector.Error as e:
        logger.error(f"MySQL Error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "error_code": e.errno if hasattr(e, 'errno') else None
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
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
