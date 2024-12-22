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

@app.route('/check-db')
def check_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        logger.info("Database connection test successful")
        return jsonify({
            "status": "success",
            "message": "Database connection successful"
        }), 200
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
