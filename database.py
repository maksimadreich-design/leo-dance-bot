from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional, List

from config import settings
from models import Base, User, DanceGroup, Subscription, Booking

DB_URL = f"sqlite+aiosqlite:///{settings.DATABASE_PATH}"

engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

DEFAULT_GROUPS = [
    # Понеділок / Середа
    {"name": "Діти (6-8 років)", "schedule_days": "Понеділок / Середа", "schedule_time": "16:00", "age_category": "6-8 років", "trainer_name": "Ірина"},
    {"name": "Діти (9-11 років)", "schedule_days": "Понеділок / Середа", "schedule_time": "17:20", "age_category": "9-11 років", "trainer_name": "Ірина"},
    {"name": "Малюки (4-5 років) - 1 група", "schedule_days": "Понеділок / Середа", "schedule_time": "18:30", "age_category": "4-5 років", "trainer_name": "Ірина"},
    {"name": "Малюки (4-5 років) - 2 група", "schedule_days": "Понеділок / Середа", "schedule_time": "19:20", "age_category": "4-5 років", "trainer_name": "Ірина"},

    # Вівторок / Четвер
    {"name": "Діти (8-10 років)", "schedule_days": "Вівторок / Четвер", "schedule_time": "16:00", "age_category": "8-10 років", "trainer_name": "Ірина"},
    {"name": "Підлітки (12-15 років)", "schedule_days": "Вівторок / Четвер", "schedule_time": "17:00", "age_category": "12-15 років", "trainer_name": "Ірина"},
    {"name": "Малюки (3-4 рочки)", "schedule_days": "Вівторок / Четвер", "schedule_time": "18:15", "age_category": "3-4 рочки", "trainer_name": "Ірина"},
    {"name": "High Heels (Основна група)", "schedule_days": "Вівторок / Четвер", "schedule_time": "19:00", "age_category": "Дорослі", "trainer_name": "Каріна"},
    {"name": "High Heels (Початківці) 👠", "schedule_days": "Вівторок / Четвер", "schedule_time": "20:00", "age_category": "Дорослі", "trainer_name": "Каріна"},

    # П'ятниця
    {"name": "CHOREO (П'ятниця)", "schedule_days": "П'ятниця", "schedule_time": "18:00", "age_category": "Всі бажаючі", "trainer_name": "Каріна"},
]

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Populate default groups if empty
    async with async_session() as session:
        result = await session.execute(select(func.count(DanceGroup.id)))
        count = result.scalar() or 0
        if count == 0:
            for g_data in DEFAULT_GROUPS:
                group = DanceGroup(**g_data)
                session.add(group)
            await session.commit()

async def get_or_create_user(telegram_id: int, full_name: str, phone: Optional[str] = None, source: str = "organic") -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                telegram_id=telegram_id,
                full_name=full_name,
                phone=phone,
                role="client",
                source=source,
                lead_status="trial_booked" if "trial" in source else "new_lead"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Automatically give 1 trial class for demo
            trial_sub = Subscription(
                user_id=user.id,
                title="Пробне тренування",
                total_classes=1,
                remaining_classes=1,
                price=150.0,
                expires_at=datetime.utcnow() + timedelta(days=14)
            )
            session.add(trial_sub)
            await session.commit()
        else:
            if source and source != "organic":
                user.source = source
                user.lead_status = "trial_booked" if "trial" in source else user.lead_status
            if phone and not user.phone:
                user.phone = phone
            await session.commit()
            await session.refresh(user)
        return user

async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

async def get_active_subscription(user_id: int) -> Optional[Subscription]:
    async with async_session() as session:
        result = await session.execute(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
                Subscription.remaining_classes > 0
            )
            .order_by(desc(Subscription.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

async def get_all_groups() -> List[DanceGroup]:
    async with async_session() as session:
        result = await session.execute(
            select(DanceGroup).where(DanceGroup.is_active == True).order_by(DanceGroup.id)
        )
        return list(result.scalars().all())

async def get_group_by_id(group_id: int) -> Optional[DanceGroup]:
    async with async_session() as session:
        result = await session.execute(select(DanceGroup).where(DanceGroup.id == group_id))
        return result.scalar_one_or_none()

async def create_booking(user_id: int, group_id: int, date_str: str) -> tuple[bool, str]:
    """
    Creates a booking. Checks if already booked and capacity.
    """
    async with async_session() as session:
        # Check existing booking
        existing = await session.execute(
            select(Booking).where(
                Booking.user_id == user_id,
                Booking.group_id == group_id,
                Booking.booking_date == date_str,
                Booking.status != "cancelled"
            )
        )
        if existing.scalar_one_or_none():
            return False, "Ви вже записані на це тренування!"

        # Check capacity
        count_res = await session.execute(
            select(func.count(Booking.id)).where(
                Booking.group_id == group_id,
                Booking.booking_date == date_str,
                Booking.status != "cancelled"
            )
        )
        booked_count = count_res.scalar() or 0

        group_res = await session.execute(select(DanceGroup).where(DanceGroup.id == group_id))
        group = group_res.scalar_one_or_none()
        if not group:
            return False, "Групу не знайдено."

        if booked_count >= group.max_capacity:
            return False, f"На жаль, всі {group.max_capacity} місць у залі вже зайняті!"

        booking = Booking(
            user_id=user_id,
            group_id=group_id,
            booking_date=date_str,
            status="booked"
        )
        session.add(booking)
        await session.commit()
        return True, "Успішно записано!"

async def get_user_bookings(user_id: int) -> List[tuple[Booking, DanceGroup]]:
    async with async_session() as session:
        result = await session.execute(
            select(Booking, DanceGroup)
            .join(DanceGroup, Booking.group_id == DanceGroup.id)
            .where(
                Booking.user_id == user_id,
                Booking.status != "cancelled"
            )
            .order_by(desc(Booking.booking_date))
            .limit(5)
        )
        return list(result.all())

async def add_subscription(user_id: int, title: str, classes_count: int, price: float, days: int = 30) -> Subscription:
    async with async_session() as session:
        sub = Subscription(
            user_id=user_id,
            title=title,
            total_classes=classes_count,
            remaining_classes=classes_count,
            price=price,
            expires_at=datetime.utcnow() + timedelta(days=days),
            is_active=True
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub

async def mark_attendance(booking_id: int, attended: bool) -> tuple[bool, str, Optional[int]]:
    """
    Marks attendance. If attended, deducts 1 class from user's active subscription.
    Returns (success, message, telegram_id)
    """
    async with async_session() as session:
        res = await session.execute(select(Booking).where(Booking.id == booking_id))
        b = res.scalar_one_or_none()
        if not b:
            return False, "Запис не знайдено", None

        user_res = await session.execute(select(User).where(User.id == b.user_id))
        user = user_res.scalar_one_or_none()

        if attended:
            b.status = "attended"
            # find active sub
            sub_res = await session.execute(
                select(Subscription).where(
                    Subscription.user_id == user.id,
                    Subscription.is_active == True,
                    Subscription.remaining_classes > 0
                ).order_by(desc(Subscription.created_at)).limit(1)
            )
            sub = sub_res.scalar_one_or_none()
            remaining = 0
            if sub:
                sub.remaining_classes -= 1
                remaining = sub.remaining_classes
                if sub.remaining_classes <= 0:
                    sub.is_active = False
            await session.commit()
            return True, f"Відвідування відмічено! Залишок занять: {remaining}", user.telegram_id if user else None
        else:
            b.status = "sick"
            await session.commit()
            return True, "Заняття збережено (хвороба/поважна причина).", user.telegram_id if user else None
