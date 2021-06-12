"""
    Flask server that will run the data crawler and provide the RESTful API
"""
from mooncaker import app

if __name__ == "__main__":
    
    app.run(host="0.0.0.0", debug=True)