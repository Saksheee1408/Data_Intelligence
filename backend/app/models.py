from sqlalchemy import Column, Integer, String, Float, DateTime
from database import Base
import datetime

class InternalSignal(Base):
    __tablename__ = "internal_signals"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    signal = Column(String)
    metric = Column(String)
    severity = Column(String)
    strength = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class InternalDataRow(Base):
    __tablename__ = "internal_data"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime)
    sales_inr = Column(Float)
    gold_stock_gm = Column(Float)
    supplier_delay_days = Column(Integer)
    advance_bookings = Column(Integer)
    upload_batch_id = Column(String)
class ExternalSignal(Base):
    __tablename__ = "external_signals"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    source = Column(String)
    signal = Column(String)
    metric = Column(String)
    severity = Column(String)
    confidence = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
