from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    full_name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=True)
    role = Column(String(20), default="client") # "client", "trainer", "admin"
    source = Column(String(50), default="organic") # "trial_heels", "trial_kids", "instagram_ad", "organic"
    lead_status = Column(String(30), default="new") # "new_lead", "trial_booked", "client", "lost"
    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")

class DanceGroup(Base):
    __tablename__ = "dance_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False) # e.g. "High Heels (Початківці)", "Діти 6-8 років"
    schedule_days = Column(String(100), nullable=False) # e.g. "Вівторок / Четвер"
    schedule_time = Column(String(20), nullable=False) # e.g. "20:00"
    age_category = Column(String(50), nullable=True) # "Дорослі", "3-4 рочки", "6-8 років", "12-15 років"
    trainer_name = Column(String(100), default="Каріна / Ірина")
    max_capacity = Column(Integer, default=14) # максимальна місткість залу
    is_active = Column(Boolean, default=True)

    bookings = relationship("Booking", back_populates="group")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(80), nullable=False) # "8 занять", "12 занять", "Пробне"
    total_classes = Column(Integer, default=8)
    remaining_classes = Column(Integer, default=8)
    price = Column(Float, default=1200.0)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("dance_groups.id"), nullable=False, index=True)
    booking_date = Column(String(10), nullable=False) # YYYY-MM-DD
    status = Column(String(20), default="booked") # "booked", "attended", "cancelled", "sick"
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    group = relationship("DanceGroup", back_populates="bookings")
