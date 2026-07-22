"""
__init__.py — Flask uygulamasını başlatır.
Veritabanını oluşturur, tüm ekibi ve admin hesabını ilk çalışmada ekler.
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'caos-super-gizli-2024'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///caos.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    from app.routes import main
    app.register_blueprint(main)

    app.jinja_env.globals['enumerate'] = enumerate

    with app.app_context():
        db.create_all()
        _kolonlari_guncelle()   # ← mevcut DB'ye yeni kolonları ekle
        _baslangic_verisi_ekle()

    return app


# ── Hafif Migration (ALTER TABLE) ─────────────────────────────────────────────
def _kolonlari_guncelle():
    """
    db.create_all() zaten var olan tabloları değiştirmez.
    Bu fonksiyon eksik kolonları ALTER TABLE ile ekler.
    Kolon zaten varsa SQLite hata fırlatır → except ile sessizce atlanır.
    """
    from sqlalchemy import text
    with db.engine.connect() as conn:
        adimlar = [
            # (tablo,  kolon,       tip ve varsayılan)
            ("vardiya", "departman",      "VARCHAR(20)"),
            ("talep",   "talep_kategori", "VARCHAR(20) DEFAULT 'Uygunluk'"),
        ]
        for tablo, kolon, tanim in adimlar:
            try:
                conn.execute(text(f"ALTER TABLE {tablo} ADD COLUMN {kolon} {tanim}"))
                conn.commit()
                print(f"  ✅ {tablo}.{kolon} kolonu eklendi.")
            except Exception:
                pass  # Kolon zaten mevcut — normal durum


# ── Başlangıç Ekibi ───────────────────────────────────────────────────────────
# Kullanıcı adı: ismin baş harfi + soyadı (küçük harf, Türkçe karakter kaldırılmış)
# Örn: Tarık İkican → t.ikican

BASLANGIC_EKIBI = [
    # ── İŞLETME ──
    {'isim': 'Tarık İkican',     'kullanici_adi': 'tarık',    'rol': 'Isletmeci'},
    {'isim': 'Batuhan Göral',    'kullanici_adi': 'batuhan',     'rol': 'Isletmeci'},

    # ── SALON ──
    {'isim': 'Nur Çördük',       'kullanici_adi': 'nur',    'rol': 'Salon'},
    {'isim': 'İkranaz Elveren',  'kullanici_adi': 'ikranaz',   'rol': 'Salon'},
    {'isim': 'Helin Polat',      'kullanici_adi': 'helin',     'rol': 'Salon'},
    {'isim': 'Nisa Yüce',        'kullanici_adi': 'nisa',      'rol': 'Salon'},
    {'isim': 'Baran İnci',       'kullanici_adi': 'baran',      'rol': 'Salon'},
    {'isim': 'Melis Yaşar',      'kullanici_adi': 'melis',     'rol': 'Salon'},

    # ── BAR ──
    {'isim': 'Kerim Emre Küçük', 'kullanici_adi': 'kerim',    'rol': 'Bar'},
    {'isim': 'Reha İnan',        'kullanici_adi': 'reha',      'rol': 'Bar'},
    {'isim': 'Tuğçe Tuncer',     'kullanici_adi': 'tugce',    'rol': 'Bar'},
    {'isim': 'Aylin Akpınar',    'kullanici_adi': 'aylin',   'rol': 'Bar'},

    # ── MUTFAK ──
    {'isim': 'Zeynep Gören',     'kullanici_adi': 'zeynep',     'rol': 'Mutfak'},
    {'isim': 'Saba Taşdemir',    'kullanici_adi': 'saba',  'rol': 'Mutfak'},
    {'isim': 'Bahar Çaryeva',    'kullanici_adi': 'bahar',   'rol': 'Mutfak'},
]


def _baslangic_verisi_ekle():
    """
    İlk çalışmada:
    1. Admin işletmeci hesabı oluşturur.
    2. Tüm gerçek ekibi veritabanına ekler (zaten varsa atlar).
    Herkese varsayılan şifre: 1234
    """
    from app.models import Personel

    eklenen = 0

    # Admin hesabı
    if not Personel.query.filter_by(kullanici_adi='admin').first():
        admin = Personel(
            kullanici_adi='admin',
            isim='Yönetici',
            rol='Isletmeci'
        )
        admin.sifre_belirle('1234')
        db.session.add(admin)
        eklenen += 1

    # Gerçek ekip
    for kayit in BASLANGIC_EKIBI:
        if not Personel.query.filter_by(kullanici_adi=kayit['kullanici_adi']).first():
            p = Personel(
                isim=kayit['isim'],
                kullanici_adi=kayit['kullanici_adi'],
                rol=kayit['rol']
            )
            p.sifre_belirle('1234')
            db.session.add(p)
            eklenen += 1

    if eklenen:
        db.session.commit()
        print(f'\n{"="*55}')
        print(f'  ✅ CAOS — {eklenen} hesap oluşturuldu (şifre: 1234)')
        print(f'{"="*55}')
        print(f'  Admin  →  kullanıcı: admin')
        for k in BASLANGIC_EKIBI:
            dep = {'Isletmeci': 'İŞLETME', 'Salon': 'SALON',
                   'Bar': 'BAR', 'Mutfak': 'MUTFAK'}.get(k['rol'], k['rol'])
            print(f'  {dep:10s} →  {k["kullanici_adi"]:18s} ({k["isim"]})')
        print(f'{"="*55}\n')
    else:
        print('ℹ️  Veritabanı zaten dolu, seed atlandı.')
