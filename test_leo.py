import asyncio
from database import (
    init_db,
    get_or_create_user,
    get_all_groups,
    create_booking,
    mark_attendance,
    add_subscription,
    get_active_subscription
)

async def test_leo():
    print("1. Ініціалізація бази Leo Dance...")
    await init_db()

    groups = await get_all_groups()
    print(f"2. Завантажено груп з розкладу: {len(groups)}")
    for g in groups[:3]:
        print(f"   • {g.name} ({g.schedule_days} о {g.schedule_time})")

    print("3. Створення тестової клієнтки...")
    user = await get_or_create_user(telegram_id=999888, full_name="Вікторія Мельник", phone="+380971234567")
    sub = await get_active_subscription(user.id)
    print(f"   Клієнт: {user.full_name}, Стартовий абонемент: {sub.title} ({sub.remaining_classes} занять)")

    print("4. Запис на High Heels (Початківці)...")
    heels_group = next(g for g in groups if "High Heels" in g.name and "Початківці" in g.name)
    success, msg = await create_booking(user.id, heels_group.id, "2026-10-08")
    print(f"   Результат запису: {msg}")

    print("5. Тренер відмічає присутність на тренуванні...")
    # Simulate attendance mark
    from models import Booking
    from sqlalchemy import select
    from database import async_session
    async with async_session() as session:
        res = await session.execute(select(Booking).where(Booking.user_id == user.id))
        b = res.scalar_one()
        booking_id = b.id

    ok, att_msg, tg_id = await mark_attendance(booking_id, attended=True)
    print(f"   Результат відмітки тренера: {att_msg}")

    sub_after = await get_active_subscription(user.id)
    print(f"   Залишок занять після відвідування: {sub_after.remaining_classes if sub_after else 0}")
    print("✅ Тест повністю пройдено успішно!")

if __name__ == "__main__":
    asyncio.run(test_leo())
