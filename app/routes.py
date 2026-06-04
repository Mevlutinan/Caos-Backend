"""
routes.py — Uygulamanın tüm sayfalarını (URL'lerini) yönetir.
"""
import io
from datetime import date, timedelta
from functools import wraps

import pandas as pd
from flask import (Blueprint, flash, redirect, render_template,
                   request, send_file, session, url_for)

from app import db
from app.models import Personel, Talep, Vardiya

main = Blueprint('main', __name__)

# Sabit listeler
VARDIYA_TIPLERI = ['Sabahçı', 'Aracı', 'Kapanış', 'Esnek', 'İzinli', 'Dinlenme', 'OFF', 'Üİ', 'BT']
GUN_ADLARI      = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']

# Her vardiya tipinin varsayılan gösterim değeri (saatler)
VARDIYA_DEGER = {
    'Sabahçı':   '08:00-16:30',   # Sabah vardiyası
    'Aracı':     '13:00-21:30',   # Ara vardiyası  ← 13:00-21:30
    'Kapanış':   '16:30-01:00',   # Kapanış vardiyası
    'Esnek':     'ESNEK',
    'İzinli':    'OFF',
    'Dinlenme':  'OFF',
    'OFF':       'OFF',
    'Üİ':        'ÜCRETLİ İZİN',
    'BT':        'BAYRAM TATİLİ',
}

# Slot-odaklı atama: Departman → Slot tipleri
DEPARTMAN_SLOTLARI = {
    'Bar':       ['Sabahçı', 'Aracı', 'Kapanış'],
    'Salon':     ['Sabahçı', 'Aracı', 'Kapanış'],
    'Mutfak':    ['Sabahçı', 'Aracı', 'Kapanış'],
    'Isletmeci': ['Esnek'],
}
DEPARTMAN_LABEL = {
    'Bar':       'BAR',
    'Salon':     'SALON',
    'Mutfak':    'MUTFAK',
    'Isletmeci': 'İŞLETME',
}


# ── Yardımcı: giriş kontrolü ──────────────────────────────────────────────────
def giris_gerekli(f):
    @wraps(f)
    def kontrol(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu sayfayı görmek için önce giriş yapmalısınız.', 'warning')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return kontrol


def sadece_yonetici(f):
    @wraps(f)
    def kontrol(*args, **kwargs):
        if session.get('rol') != 'Isletmeci':
            flash('Bu sayfaya yalnızca yöneticiler erişebilir.', 'danger')
            return redirect(url_for('main.personel_panel'))
        return f(*args, **kwargs)
    return kontrol


# ── Ana Sayfa ─────────────────────────────────────────────────────────────────
@main.route('/')
def index():
    return render_template('index.html')


# ── Giriş ─────────────────────────────────────────────────────────────────────
@main.route('/login', methods=['GET', 'POST'])
def login():
    if 'kullanici_id' in session:
        if session.get('rol') == 'Isletmeci':
            return redirect(url_for('main.dashboard'))
        return redirect(url_for('main.personel_panel'))

    if request.method == 'POST':
        kullanici_adi = request.form.get('kullanici_adi', '').strip()
        sifre         = request.form.get('sifre', '')
        personel = Personel.query.filter_by(kullanici_adi=kullanici_adi).first()

        if personel and personel.sifre_kontrol(sifre):
            session['kullanici_id'] = personel.id
            session['isim']         = personel.isim
            session['rol']          = personel.rol
            # Rol bazlı yönlendirme
            if personel.rol == 'Isletmeci':
                return redirect(url_for('main.dashboard'))
            return redirect(url_for('main.personel_panel'))
        else:
            flash('Kullanıcı adı veya şifre hatalı!', 'danger')

    return render_template('login.html')


# ── Dashboard ─────────────────────────────────────────────────────────────────
@main.route('/dashboard')
@giris_gerekli
@sadece_yonetici
def dashboard():
    # Bekleyen talep sayısını say (kart üzerinde rozet göstermek için)
    bekleyen = Talep.query.filter_by(durum='Beklemede').count()
    return render_template(
        'dashboard.html',
        isim=session['isim'],
        rol=session['rol'],
        bekleyen_talep=bekleyen,
    )


# ── Çıkış ─────────────────────────────────────────────────────────────────────
@main.route('/logout')
def logout():
    session.clear()
    flash('Başarıyla çıkış yapıldı.', 'success')
    return redirect(url_for('main.index'))


# ── Personel Yönetimi ─────────────────────────────────────────────────────────
@main.route('/personel-yonetimi', methods=['GET', 'POST'])
@giris_gerekli
@sadece_yonetici
def personel_yonetimi():
    ROL_SECENEKLERI = ['Bar', 'Salon', 'Mutfak', 'Isletmeci']

    if request.method == 'POST':
        islem = request.form.get('islem', '')

        # ── Yeni personel ekle ──
        if islem == 'ekle':
            isim          = request.form.get('isim', '').strip()
            kullanici_adi = request.form.get('kullanici_adi', '').strip()
            sifre         = request.form.get('sifre', '').strip()
            rol           = request.form.get('rol', '').strip()

            if not all([isim, kullanici_adi, sifre, rol]):
                flash('Lütfen tüm alanları doldurun.', 'danger')
            elif Personel.query.filter_by(kullanici_adi=kullanici_adi).first():
                flash(f'"{kullanici_adi}" kullanıcı adı zaten alınmış.', 'danger')
            else:
                yeni = Personel(
                    isim=isim,
                    kullanici_adi=kullanici_adi,
                    rol=rol
                )
                yeni.sifre_belirle(sifre)
                db.session.add(yeni)
                db.session.commit()
                flash(f'✅ {isim} başarıyla sisteme eklendi!', 'success')

        # ── Personel sil ──
        elif islem == 'sil':
            pid = request.form.get('personel_id', type=int)
            p   = Personel.query.get(pid)
            if p and p.rol != 'Isletmeci':
                db.session.delete(p)
                db.session.commit()
                flash(f'🗑️ {p.isim} sistemden silindi.', 'warning')
            elif p and p.rol == 'Isletmeci':
                flash('İşletmeci hesabı silinemez.', 'danger')

        return redirect(url_for('main.personel_yonetimi'))

    # GET: personel listesini getir
    personeller = Personel.query.order_by(Personel.rol, Personel.isim).all()
    return render_template(
        'personel_yonetimi.html',
        personeller=personeller,
        rol_secenekleri=ROL_SECENEKLERI,
        isim=session['isim'],
        rol=session['rol'],
    )


# ── Vardiya Planlama (Slot-Odaklı) ──────────────────────────────────────────────
@main.route('/vardiya-planlama', methods=['GET', 'POST'])
@giris_gerekli
@sadece_yonetici
def vardiya_planlama():
    hafta_str = request.args.get('hafta') or request.form.get('hafta')
    if hafta_str:
        hafta_basi = date.fromisoformat(hafta_str)
    else:
        bugun = date.today()
        hafta_basi = bugun - timedelta(days=bugun.weekday())

    hafta_gunleri = [hafta_basi + timedelta(days=i) for i in range(7)]
    hafta_bitis   = hafta_gunleri[-1]

    # ── Kaydetme ──
    if request.method == 'POST':
        # Tüm haftanın vardiyalarını sil, formdan gelenleri yeniden yaz
        Vardiya.query.filter(
            Vardiya.tarih >= hafta_basi,
            Vardiya.tarih <= hafta_bitis
        ).delete()
        db.session.flush()

        # Çakışma kontrolü: aynı kişi aynı güne iki kez atanamaz
        atamalar = []  # (pid, gun, slot_tipi)
        atanan_gunler = {}  # {(pid, gun_iso): slot_tipi}
        cakisma = False

        for dep_key, slot_listesi in DEPARTMAN_SLOTLARI.items():
            for slot_tipi in slot_listesi:
                for gun in hafta_gunleri:
                    form_key = f"slot_{dep_key}_{slot_tipi}_{gun.isoformat()}"
                    pid = request.form.get(form_key, type=int)
                    if not pid:
                        continue
                    cakisma_key = (pid, gun.isoformat())
                    if cakisma_key in atanan_gunler:
                        p_obj = Personel.query.get(pid)
                        isim  = p_obj.isim if p_obj else str(pid)
                        flash(
                            f'⚠️ Çakışma: {isim} — '
                            f'{gun.strftime("%d.%m")} gününde '
                            f'{atanan_gunler[cakisma_key]} ve {slot_tipi} '
                            f'aynı anda atanamaz!',
                            'danger'
                        )
                        cakisma = True
                    else:
                        atanan_gunler[cakisma_key] = slot_tipi
                        atamalar.append((pid, gun, slot_tipi))

        if not cakisma:
            for pid, gun, slot_tipi in atamalar:
                deger = VARDIYA_DEGER.get(slot_tipi, slot_tipi)
                db.session.add(Vardiya(
                    personel_id=pid, tarih=gun,
                    vardiya_tipi=slot_tipi, deger=deger
                ))
            db.session.commit()
            flash('✅ Vardiyalar kaydedildi!', 'success')
        else:
            db.session.rollback()

        return redirect(url_for('main.vardiya_planlama', hafta=hafta_basi.isoformat()))

    # ── Görüntüleme ──
    # slot_map[dep][slot_tipi][tarih_str] = personel_id
    vardiyalar = Vardiya.query.filter(
        Vardiya.tarih >= hafta_basi,
        Vardiya.tarih <= hafta_bitis
    ).all()

    tum_personel = {p.id: p for p in Personel.query.all()}

    slot_map = {}
    for v in vardiyalar:
        p = tum_personel.get(v.personel_id)
        if not p:
            continue
        (slot_map
            .setdefault(p.rol, {})
            .setdefault(v.vardiya_tipi, {})
            .__setitem__(v.tarih.isoformat(), v.personel_id))

    # Departmana göre personel listeleri
    personel_by_dep = {
        dep: Personel.query.filter_by(rol=dep).order_by(Personel.isim).all()
        for dep in DEPARTMAN_SLOTLARI
    }

    # Onaylanmış izinler: {personel_id: [tarih_str, ...]}
    uyarilar_q = Talep.query.filter(
        Talep.tarih >= hafta_basi,
        Talep.tarih <= hafta_bitis,
        Talep.durum == 'Onaylandi'
    ).all()
    izinli_gunler = {}
    for u in uyarilar_q:
        izinli_gunler.setdefault(u.personel_id, []).append(u.tarih.isoformat())

    return render_template(
        'vardiya_planlama.html',
        dep_slotlari=DEPARTMAN_SLOTLARI,
        dep_label=DEPARTMAN_LABEL,
        hafta_gunleri=hafta_gunleri,
        hafta_basi=hafta_basi,
        hafta_bitis=hafta_bitis,
        slot_map=slot_map,
        personel_by_dep=personel_by_dep,
        izinli_gunler=izinli_gunler,
        tum_personel=tum_personel,
        vardiya_deger=VARDIYA_DEGER,
        gun_adlari=GUN_ADLARI,
        onceki_hafta=(hafta_basi - timedelta(weeks=1)).isoformat(),
        sonraki_hafta=(hafta_basi + timedelta(weeks=1)).isoformat(),
    )



# ── Excel İndir ───────────────────────────────────────────────────────────────
@main.route('/vardiya-excel')
@giris_gerekli
@sadece_yonetici
def vardiya_excel():
    hafta_str = request.args.get('hafta')
    if hafta_str:
        hafta_basi = date.fromisoformat(hafta_str)
    else:
        bugun = date.today()
        hafta_basi = bugun - timedelta(days=bugun.weekday())

    hafta_gunleri = [hafta_basi + timedelta(days=i) for i in range(7)]
    hafta_bitis   = hafta_gunleri[-1]

    personeller = Personel.query.order_by(Personel.rol, Personel.isim).all()
    vardiyalar  = Vardiya.query.filter(
        Vardiya.tarih >= hafta_basi,
        Vardiya.tarih <= hafta_bitis
    ).all()

    vardiya_map = {}
    for v in vardiyalar:
        goster = v.deger or VARDIYA_DEGER.get(v.vardiya_tipi, v.vardiya_tipi)
        vardiya_map.setdefault(v.personel_id, {})[v.tarih.isoformat()] = goster

    # DataFrame oluştur
    satirlar = []
    for p in personeller:
        satir = {'Personel': p.isim, 'Departman': p.rol}
        for i, gun in enumerate(hafta_gunleri):
            sutun = f"{GUN_ADLARI[i]} ({gun.strftime('%d.%m')})"
            satir[sutun] = vardiya_map.get(p.id, {}).get(gun.isoformat(), '-')
        satirlar.append(satir)

    df = pd.DataFrame(satirlar)

    # Excel çıktısı
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Vardiya Planı')
        ws = writer.sheets['Vardiya Planı']
        # Sütun genişlikleri
        ws.column_dimensions['A'].width = 22
        ws.column_dimensions['B'].width = 14
        for i, col in enumerate(['C','D','E','F','G','H','I']):
            ws.column_dimensions[col].width = 18

    output.seek(0)
    dosya_adi = f"CAOS_Vardiya_{hafta_basi.strftime('%Y_%m_%d')}.xlsx"
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=dosya_adi
    )


# ── Haftalık Çizelge Görüntüleme ─────────────────────────────────────────────
@main.route('/haftalik-cizelge')
@giris_gerekli
def haftalik_cizelge():
    """
    Tüm personelin (yönetici veya değil) okuyabileceği
    salt-okunur haftalık vardiya tablosu.
    """
    hafta_str = request.args.get('hafta')
    if hafta_str:
        hafta_basi = date.fromisoformat(hafta_str)
    else:
        bugun = date.today()
        hafta_basi = bugun - timedelta(days=bugun.weekday())

    hafta_gunleri = [hafta_basi + timedelta(days=i) for i in range(7)]
    hafta_bitis   = hafta_gunleri[-1]

    # Tüm personeli çek
    personeller = Personel.query.order_by(Personel.isim).all()

    # Bu haftanın vardiyalarını çek
    vardiyalar = Vardiya.query.filter(
        Vardiya.tarih >= hafta_basi,
        Vardiya.tarih <= hafta_bitis
    ).all()

    # Pivot: {personel_id: {tarih_str: {'tipi':..,'deger':..}}}
    vardiya_map = {}
    for v in vardiyalar:
        goster = v.deger or VARDIYA_DEGER.get(v.vardiya_tipi, v.vardiya_tipi)
        vardiya_map.setdefault(v.personel_id, {})[v.tarih.isoformat()] = {
            'tipi':  v.vardiya_tipi,
            'deger': goster,
        }

    # Departman sırası ve görünen adları
    DEPARTMAN_SIRASI = ['Isletmeci', 'Salon', 'Bar', 'Mutfak']
    DEPARTMAN_LABEL  = {
        'Isletmeci': 'İŞLETME',
        'Salon':     'SALON',
        'Bar':       'BAR',
        'Mutfak':    'MUTFAK',
    }

    # Her departmandaki personeli grupla
    gruplar = {}
    for dep in DEPARTMAN_SIRASI:
        dep_personel = [p for p in personeller if p.rol == dep]
        if dep_personel:
            gruplar[dep] = dep_personel

    return render_template(
        'haftalik_cizelge.html',
        gruplar=gruplar,
        dep_label=DEPARTMAN_LABEL,
        hafta_gunleri=hafta_gunleri,
        hafta_basi=hafta_basi,
        hafta_bitis=hafta_bitis,
        vardiya_map=vardiya_map,
        gun_adlari=GUN_ADLARI,
        onceki_hafta=(hafta_basi - timedelta(weeks=1)).isoformat(),
        sonraki_hafta=(hafta_basi + timedelta(weeks=1)).isoformat(),
        rol=session.get('rol'),
    )


# ── Personel Paneli ───────────────────────────────────────────────────────────
@main.route('/personel-panel')
@giris_gerekli
def personel_panel():
    pid = session['kullanici_id']

    # Bu haftanın kişisel vardiyaları
    bugun = date.today()
    hafta_basi   = bugun - timedelta(days=bugun.weekday())
    hafta_bitis  = hafta_basi + timedelta(days=6)
    hafta_gunleri = [hafta_basi + timedelta(days=i) for i in range(7)]

    vardiyalar = (Vardiya.query
                  .filter_by(personel_id=pid)
                  .filter(Vardiya.tarih >= hafta_basi, Vardiya.tarih <= hafta_bitis)
                  .order_by(Vardiya.tarih)
                  .all())

    # Son 15 kişisel talep
    talepler = (Talep.query
                .filter_by(personel_id=pid)
                .order_by(Talep.olusturma.desc())
                .limit(15)
                .all())

    return render_template(
        'personel_dashboard.html',
        isim=session['isim'],
        rol=session['rol'],
        vardiyalar=vardiyalar,
        talepler=talepler,
        hafta_basi=hafta_basi,
        hafta_gunleri=hafta_gunleri,
        gun_adlari=GUN_ADLARI,
        vardiya_deger=VARDIYA_DEGER,
        bugun=bugun,
    )


# ── Talep Gönder (POST) ───────────────────────────────────────────────────────
@main.route('/talep-gonder', methods=['POST'])
@giris_gerekli
def talep_gonder():
    pid        = session['kullanici_id']
    tarih_str  = request.form.get('tarih', '').strip()
    talep_turu = request.form.get('talep_turu', '').strip()
    aciklama   = request.form.get('aciklama', '').strip()

    if not tarih_str or not talep_turu:
        flash('Tarih ve talep türü zorunludur.', 'danger')
        return redirect(url_for('main.personel_panel'))

    try:
        tarih = date.fromisoformat(tarih_str)
    except ValueError:
        flash('Geçersiz tarih formatı.', 'danger')
        return redirect(url_for('main.personel_panel'))

    yeni_talep = Talep(
        personel_id=pid,
        tarih=tarih,
        talep_turu=talep_turu,
        aciklama=aciklama,
        durum='Beklemede'
    )
    db.session.add(yeni_talep)
    db.session.commit()
    flash('✅ Talebiniz iletildi! Yönetici onayını bekliyor.', 'success')
    return redirect(url_for('main.personel_panel'))


# ── Haftalık Uygunluk Gönder (POST) ──────────────────────────────────────────
# Uygunluk formundan gelen 7 günlük paket; sadece "Fark Etmez" harici günler kaydedilir.
UYGUNLUK_TURLERI = ['Sadece Sabah', 'Sadece Ara', 'Sadece Kapanış', 'OFF İstiyorum']

@main.route('/haftalik-uygunluk-gonder', methods=['POST'])
@giris_gerekli
def haftalik_uygunluk_gonder():
    pid       = session['kullanici_id']
    hafta_str = request.form.get('hafta_basi', '').strip()

    if not hafta_str:
        flash('Hafta bilgisi eksik.', 'danger')
        return redirect(url_for('main.personel_panel'))

    hafta_basi   = date.fromisoformat(hafta_str)
    hafta_bitis  = hafta_basi + timedelta(days=6)
    hafta_gunleri = [hafta_basi + timedelta(days=i) for i in range(7)]

    # Önceki uygunluk kayıtlarını temizle (upsert mantığı)
    (Talep.query
     .filter(
         Talep.personel_id == pid,
         Talep.tarih >= hafta_basi,
         Talep.tarih <= hafta_bitis,
         Talep.talep_turu.in_(UYGUNLUK_TURLERI)
     )
     .delete(synchronize_session=False))
    db.session.flush()

    # Sadece "Fark Etmez" harici günleri kaydet
    eklenen = 0
    for i, gun in enumerate(hafta_gunleri):
        durum = request.form.get(f'gun_{i}_durum', 'Fark Etmez').strip()
        not_  = request.form.get(f'gun_{i}_not',  '').strip()

        if durum == 'Fark Etmez':
            continue

        db.session.add(Talep(
            personel_id=pid,
            tarih=gun,
            talep_turu=durum,
            aciklama=not_ or None,
            durum='Beklemede'
        ))
        eklenen += 1

    db.session.commit()

    if eklenen:
        flash(f'✅ {eklenen} günlük uygunluk bilginiz yöneticiye iletildi!', 'success')
    else:
        flash('Tüm günler "Uygun" — yöneticiye iletilecek özel durum yok.', 'info')

    return redirect(url_for('main.personel_panel'))



# ── Talep Yönetimi (Admin) ────────────────────────────────────────────────────
@main.route('/talep-yonetimi', methods=['GET', 'POST'])
@giris_gerekli
@sadece_yonetici
def talep_yonetimi():
    if request.method == 'POST':
        talep_id = request.form.get('talep_id', type=int)
        islem    = request.form.get('islem', '')
        talep    = Talep.query.get(talep_id)

        if talep:
            if islem == 'onayla':
                talep.durum = 'Onaylandi'
                flash(f'✅ {talep.personel.isim} — talep onaylandı.', 'success')
            elif islem == 'reddet':
                talep.durum = 'Reddedildi'
                flash(f'❌ {talep.personel.isim} — talep reddedildi.', 'warning')
            db.session.commit()

        return redirect(url_for('main.talep_yonetimi'))

    # Bekleyenler önce, sonra tarihsel sıra
    talepler = (Talep.query
                .order_by(
                    Talep.durum == 'Beklemede',   # True=1, False=0 → ters sırala
                    Talep.olusturma.desc()
                )
                .all())

    # Durum bazlı sayım
    bekleyen  = sum(1 for t in talepler if t.durum == 'Beklemede')
    onaylanan = sum(1 for t in talepler if t.durum == 'Onaylandi')
    reddedilen = sum(1 for t in talepler if t.durum == 'Reddedildi')

    return render_template(
        'talep_yonetimi.html',
        talepler=talepler,
        bekleyen=bekleyen,
        onaylanan=onaylanan,
        reddedilen=reddedilen,
        isim=session['isim'],
        rol=session['rol'],
    )
