"""
models.py — Veritabanı tablolarını tanımlar.
Şu an sadece 'Personel' tablosu var.
"""
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class Personel(db.Model):
    """Kafe personelini temsil eden tablo."""
    __tablename__ = 'personel'

    id            = db.Column(db.Integer, primary_key=True)
    kullanici_adi = db.Column(db.String(50), unique=True, nullable=False)
    isim          = db.Column(db.String(100), nullable=False)
    sifre_hash    = db.Column(db.String(256), nullable=False)
    # Rol seçenekleri: Bar, Salon, Mutfak, Isletmeci
    rol           = db.Column(db.String(20), nullable=False)

    def sifre_belirle(self, sifre: str):
        """Şifreyi güvenli şekilde (hash'leyerek) kaydeder."""
        self.sifre_hash = generate_password_hash(sifre)

    def sifre_kontrol(self, sifre: str) -> bool:
        """Girilen şifreyi kayıtlı hash ile karşılaştırır."""
        return check_password_hash(self.sifre_hash, sifre)

    def __repr__(self):
        return f'<Personel {self.kullanici_adi} [{self.rol}]>'
