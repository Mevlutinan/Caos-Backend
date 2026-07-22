"""
app/models/__init__.py
Tüm veritabanı tablolarını burada tanımlıyoruz.
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


# ── Personel ──────────────────────────────────────────────────────────────────
class Personel(db.Model):
    """Kafe personelini temsil eden tablo."""
    __tablename__ = 'personel'

    id            = db.Column(db.Integer, primary_key=True)
    kullanici_adi = db.Column(db.String(50), unique=True, nullable=False)
    isim          = db.Column(db.String(100), nullable=False)
    sifre_hash    = db.Column(db.String(256), nullable=False)
    rol           = db.Column(db.String(20), nullable=False)  # Bar, Salon, Mutfak, Isletmeci

    talepler  = db.relationship('Talep',   backref='personel', lazy=True)
    vardiyalar = db.relationship('Vardiya', backref='personel', lazy=True)

    def sifre_belirle(self, sifre: str):
        self.sifre_hash = generate_password_hash(sifre)

    def sifre_kontrol(self, sifre: str) -> bool:
        return check_password_hash(self.sifre_hash, sifre)

    def __repr__(self):
        return f'<Personel {self.kullanici_adi} [{self.rol}]>'


# ── Talep (İzin/Uygunluk İsteği) ─────────────────────────────────────────────
class Talep(db.Model):
    """
    Personelin izin veya uygunluk taleplerini tutar.
    Durum: Beklemede → Onaylandi veya Reddedildi
    """
    __tablename__ = 'talep'

    id             = db.Column(db.Integer, primary_key=True)
    personel_id    = db.Column(db.Integer, db.ForeignKey('personel.id'), nullable=False)
    tarih          = db.Column(db.Date, nullable=False)
    talep_turu     = db.Column(db.String(50), nullable=False)
    talep_kategori = db.Column(db.String(20), default='Uygunluk')  # 'Uygunluk' | 'İzin'
    aciklama       = db.Column(db.String(500))
    durum          = db.Column(db.String(20), default='Beklemede')  # Beklemede/Onaylandi/Reddedildi
    olusturma      = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Talep {self.personel_id} {self.tarih} {self.durum}>'


# ── Vardiya ───────────────────────────────────────────────────────────────────
class Vardiya(db.Model):
    """
    Bir personele belirli bir tarih için atanan vardiyayı tutar.
    - vardiya_tipi: Sabahçı, Kapanış vb. (renk grubu için)
    - deger: Gösterilecek metin — "08:00-16:30", "OFF", "BT", "Üİ" vb.
    """
    __tablename__ = 'vardiya'

    id           = db.Column(db.Integer, primary_key=True)
    personel_id  = db.Column(db.Integer, db.ForeignKey('personel.id'), nullable=False)
    tarih        = db.Column(db.Date, nullable=False)
    vardiya_tipi = db.Column(db.String(30), nullable=False)
    departman    = db.Column(db.String(20))  # 'Bar' | 'Salon' | 'Mutfak' | 'Isletmeci'
    # Hüerede görünecek saat/kod — boşsa varsayılan kullanılır
    deger        = db.Column(db.String(50))

    __table_args__ = (
        db.UniqueConstraint('personel_id', 'tarih', name='uq_personel_tarih'),
    )

    def __repr__(self):
        return f'<Vardiya {self.personel_id} {self.tarih} {self.vardiya_tipi}>'

