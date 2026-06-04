"""
run.py — Uygulamayı başlatmak için bu dosyayı çalıştır.
Terminalde: python run.py
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    # host='0.0.0.0' → aynı Wi-Fi'daki telefon/tablet de bağlanabilir
    # Telefondan erişmek için: http://<bilgisayarın IP'si>:5000
    app.run(host='0.0.0.0', port=5000, debug=True)
