"""Parking models."""

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Float, Integer, JSON, Text, UniqueConstraint
from fibaro_core.database import Base


class ParkingSession(Base):
    __tablename__ = "parkering"
    __table_args__ = (UniqueConstraint("source_system", "parking_id", name="parkering_uq"),)

    id = Column(BigInteger, primary_key=True, index=True)
    parking_area = Column(Text, nullable=False)
    source_system = Column(Text, nullable=False)
    area_number = Column(Integer, nullable=False, index=True)
    parking_id = Column(BigInteger, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True, index=True)
    parking_time_min = Column(Float, nullable=True)
    fee_ex_vat = Column(Float, nullable=True)
    fee_inc_vat = Column(Float, nullable=True)
    fee_vat = Column(Float, nullable=True)
    car_license_number = Column(Text, nullable=True, index=True)
    user_interface = Column(Text, nullable=True)
    subtype = Column(Text, nullable=True)
    status = Column(Text, nullable=False, index=True)
    imported_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw_filename = Column(Text, nullable=True)


class ParkingVehicle(Base):
    __tablename__ = "kjoretoy"

    plate = Column(Text, primary_key=True)
    navn = Column(Text, nullable=True)
    omrade = Column(Text, nullable=True, index=True)
    omrade_kilde = Column(Text, nullable=True)
    omrade_oppdatert = Column(DateTime, nullable=True)
    sun2_id = Column(Text, nullable=True, index=True)
    notat = Column(Text, nullable=True)
    first_seen = Column(DateTime, nullable=True, index=True)
    last_seen = Column(DateTime, nullable=True, index=True)
    parkering_count = Column(BigInteger, nullable=True)
    paid_total = Column(Float, nullable=True)
    svv_fetched_at = Column(DateTime, nullable=True, index=True)
    svv_status = Column(Integer, nullable=True)
    svv_error = Column(Text, nullable=True)
    svv_data = Column(JSON, nullable=True)
    car_info_fetched_at = Column(DateTime, nullable=True, index=True)
    car_info_status = Column(Integer, nullable=True)
    car_info_error = Column(Text, nullable=True)
    car_info_url = Column(Text, nullable=True)
    car_info_data = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ParkingVehicleDetails(Base):
    __tablename__ = "kjoretoy_nokkeldata"

    plate = Column(Text, primary_key=True)
    vin = Column(Text, nullable=True)
    merke = Column(Text, nullable=True, index=True)
    modell = Column(Text, nullable=True, index=True)
    typebetegnelse = Column(Text, nullable=True)
    kjoretoyklasse_kode = Column(Text, nullable=True)
    kjoretoyklasse_navn = Column(Text, nullable=True, index=True)
    registreringsstatus_kode = Column(Text, nullable=True)
    registreringsstatus_tekst = Column(Text, nullable=True)
    forstegangsregistrert_norge = Column(Date, nullable=True)
    pkk_kontrollfrist = Column(Date, nullable=True)
    egenvekt_kg = Column(Integer, nullable=True)
    nyttelast_kg = Column(Integer, nullable=True)
    tillatt_totalvekt_kg = Column(Integer, nullable=True)
    tillatt_vogntogvekt_kg = Column(Integer, nullable=True)
    tillatt_tilhengervekt_med_brems_kg = Column(Integer, nullable=True)
    tillatt_tilhengervekt_uten_brems_kg = Column(Integer, nullable=True)
    seter_totalt = Column(Integer, nullable=True)
    lengde_mm = Column(Integer, nullable=True)
    bredde_mm = Column(Integer, nullable=True)
    hoyde_mm = Column(Integer, nullable=True)
    rekkevidde_wltp_km = Column(Integer, nullable=True)
    elforbruk_wltp_wh_km = Column(Integer, nullable=True)
    motoreffekt_samlet_kw = Column(Float, nullable=True)
    motoreffekt_kontinuerlig_kw = Column(Float, nullable=True)
    maks_hastighet_kmt = Column(Integer, nullable=True)
    stoy_db = Column(Integer, nullable=True)
    abs = Column(Boolean, nullable=True)
    farge = Column(Text, nullable=True)
    svv_godkjennings_id = Column(Text, nullable=True)
    svv_teknisk_gyldig_fra = Column(Date, nullable=True)
    sist_synkronisert = Column(DateTime, default=datetime.utcnow, nullable=False)
