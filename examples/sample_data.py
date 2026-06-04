"""
CAOS – Cafe Automation and Optimization System
Örnek veri: Pydantic modellerinin doğru çalıştığını göstermek için
hafızada oluşturulmuş sentetik veri seti.

Çalıştırmak için:
    python examples/sample_data.py
"""

from datetime import date, time

from app.models import (
    DailyShiftBlock,
    DayOfWeek,
    EmployeeRole,
    FullTimeConstraints,
    FullTimeEmployee,
    PartTimeConstraints,
    PartTimeEmployee,
    ShiftAssignment,
    ShiftDefinition,
    ShiftPreference,
    ShiftType,
    TimeSlot,
    UnavailabilityWindow,
    WeeklyScheduleTemplate,
)


# ---------------------------------------------------------------------------
# 1. Vardiya tanımları
# ---------------------------------------------------------------------------

morning_shift = ShiftDefinition(
    name="Sabah Vardiyası",
    shift_type=ShiftType.MORNING,
    time_slot=TimeSlot(start=time(7, 0), end=time(13, 0)),
    min_staff_required=2,
)

afternoon_shift = ShiftDefinition(
    name="Öğle Vardiyası",
    shift_type=ShiftType.AFTERNOON,
    time_slot=TimeSlot(start=time(11, 0), end=time(17, 0)),
    min_staff_required=2,
)

evening_shift = ShiftDefinition(
    name="Akşam Vardiyası",
    shift_type=ShiftType.EVENING,
    time_slot=TimeSlot(start=time(16, 0), end=time(22, 0)),
    min_staff_required=2,
)

print("✅ Vardiya tanımları oluşturuldu.")
print(f"   - {morning_shift.name}  ({morning_shift.duration_hours}s)")
print(f"   - {afternoon_shift.name} ({afternoon_shift.duration_hours}s)")
print(f"   - {evening_shift.name}  ({evening_shift.duration_hours}s)")


# ---------------------------------------------------------------------------
# 2. Part-time çalışan – Ayşe (üniversite öğrencisi)
# ---------------------------------------------------------------------------

ayse = PartTimeEmployee(
    full_name="Ayşe Kaya",
    email="ayse.kaya@cafe.com",
    phone="+90 555 111 2233",
    role=EmployeeRole.BARISTA,
    hire_date=date(2024, 9, 1),
    constraints=PartTimeConstraints(
        max_hours_per_week=20,
        max_shifts_per_week=4,
        unavailability_windows=[
            # Pazartesi sabah dersi
            UnavailabilityWindow(
                day=DayOfWeek.MONDAY,
                time_slot=TimeSlot(start=time(9, 0), end=time(13, 0)),
                reason="Üniversite: Algoritmalar dersi",
            ),
            # Çarşamba tüm gün
            UnavailabilityWindow(
                day=DayOfWeek.WEDNESDAY,
                time_slot=TimeSlot(start=time(8, 0), end=time(18, 0)),
                reason="Üniversite: Laboratuvar günü",
            ),
            # Cuma öğleden sonra
            UnavailabilityWindow(
                day=DayOfWeek.FRIDAY,
                time_slot=TimeSlot(start=time(12, 0), end=time(16, 0)),
                reason="Üniversite: Staj raporu toplantısı",
            ),
        ],
    ),
    preferences=[
        ShiftPreference(
            day=DayOfWeek.SATURDAY,
            time_slot=TimeSlot(start=time(10, 0), end=time(16, 0)),
            priority=8,
        )
    ],
)

print(f"\n✅ Part-time çalışan oluşturuldu: {ayse.full_name}")
print(f"   Haftalık maks. saat   : {ayse.constraints.max_hours_per_week}")
print(f"   Kısıt penceresi sayısı: {len(ayse.constraints.unavailability_windows)}")

# Pazartesi 09:00-11:00 arası müsait mi? → Hayır (okul 09-13)
pzt_check = ayse.is_available(DayOfWeek.MONDAY, time(9, 0), time(11, 0))
print(f"   Pazartesi 09-11 müsait mi? → {'Evet' if pzt_check else 'Hayır (hard constraint)'}")

# Pazartesi 14:00-18:00 arası müsait mi? → Evet
pzt_check2 = ayse.is_available(DayOfWeek.MONDAY, time(14, 0), time(18, 0))
print(f"   Pazartesi 14-18 müsait mi? → {'Evet' if pzt_check2 else 'Hayır'}")


# ---------------------------------------------------------------------------
# 3. Full-time çalışan – Mehmet (süpervizör)
# ---------------------------------------------------------------------------

mehmet = FullTimeEmployee(
    full_name="Mehmet Demir",
    email="mehmet.demir@cafe.com",
    phone="+90 533 444 5566",
    role=EmployeeRole.SUPERVISOR,
    hire_date=date(2022, 3, 15),
    constraints=FullTimeConstraints(
        max_hours_per_week=45,
        min_full_days_off_per_week=1,
        max_consecutive_working_days=6,
        preferred_days_off=[DayOfWeek.SUNDAY],
    ),
    preferences=[
        ShiftPreference(
            day=DayOfWeek.MONDAY,
            time_slot=TimeSlot(start=time(7, 0), end=time(13, 0)),
            priority=7,
        )
    ],
)

print(f"\n✅ Full-time çalışan oluşturuldu: {mehmet.full_name}")
print(f"   Haftalık maks. saat       : {mehmet.constraints.max_hours_per_week}")
print(f"   Min. tam gün izin/hafta   : {mehmet.constraints.min_full_days_off_per_week}")
print(f"   Tercih edilen izin günleri: {[d.value for d in mehmet.constraints.preferred_days_off]}")


# ---------------------------------------------------------------------------
# 4. Haftalık vardiya şablonu
# ---------------------------------------------------------------------------

template = WeeklyScheduleTemplate(
    name="Standart Hafta – Yaz Sezonu",
    week_start_date=date(2025, 7, 7),  # Pazartesi
    daily_blocks=[
        DailyShiftBlock(day=DayOfWeek.MONDAY,    shifts=[morning_shift, afternoon_shift, evening_shift]),
        DailyShiftBlock(day=DayOfWeek.TUESDAY,   shifts=[morning_shift, afternoon_shift, evening_shift]),
        DailyShiftBlock(day=DayOfWeek.WEDNESDAY, shifts=[morning_shift, afternoon_shift, evening_shift]),
        DailyShiftBlock(day=DayOfWeek.THURSDAY,  shifts=[morning_shift, afternoon_shift, evening_shift]),
        DailyShiftBlock(day=DayOfWeek.FRIDAY,    shifts=[morning_shift, afternoon_shift, evening_shift]),
        DailyShiftBlock(day=DayOfWeek.SATURDAY,  shifts=[morning_shift, afternoon_shift, evening_shift]),
        DailyShiftBlock(day=DayOfWeek.SUNDAY,    shifts=[morning_shift, afternoon_shift]),
    ],
)

print(f"\n✅ Haftalık şablon oluşturuldu: {template.name}")
print(f"   Toplam haftalık saat: {template.total_weekly_shift_hours()}")
print(f"   Pazar bloğu       : {template.get_day_block(DayOfWeek.SUNDAY)}")


# ---------------------------------------------------------------------------
# 5. Vardiya ataması
# ---------------------------------------------------------------------------

assignment = ShiftAssignment(
    week_start_date=date(2025, 7, 7),
    day=DayOfWeek.MONDAY,
    shift_id=morning_shift.id,
    employee_id=mehmet.id,
    is_confirmed=True,
    note="Manuel ataması – pilot hafta.",
)

print(f"\n✅ Vardiya ataması oluşturuldu:")
print(f"   Çalışan ID : {assignment.employee_id}")
print(f"   Vardiya ID : {assignment.shift_id}")
print(f"   Gün        : {assignment.day.value}")
print(f"   Onaylı mı? : {assignment.is_confirmed}")

print("\n🎉 Tüm modeller hatasız yüklendi ve doğrulandı.")
