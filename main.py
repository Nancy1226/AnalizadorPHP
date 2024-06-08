from website import create_app
from website.auth import auth  # Importa auth

app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)