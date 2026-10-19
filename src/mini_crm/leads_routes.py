
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mini_crm.auth import get_db, get_current_user, require_admin
from mini_crm.models import Lead, User
from mini_crm.schemas import LeadCreate, LeadUpdate, LeadResponse

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.post("/", response_model=LeadResponse, status_code=201)
def create_lead(
    data: LeadCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    existing = db.query(Lead).filter(Lead.email == str(data.email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Lead email already exists")

    lead = Lead(**data.model_dump())
    db.add(lead)

    try:
        db.commit()
        db.refresh(lead)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Lead email already exists")

    return lead


@router.get("/", response_model=list[LeadResponse])
def list_leads(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(Lead).order_by(Lead.id).all()


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lead = db.get(Lead, lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    data: LeadUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    lead = db.get(Lead, lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    duplicate = db.query(Lead).filter(
        Lead.email == str(data.email),
        Lead.id != lead_id,
    ).first()

    if duplicate:
        raise HTTPException(status_code=409, detail="Another lead uses this email")

    for field, value in data.model_dump().items():
        setattr(lead, field, value)

    try:
        db.commit()
        db.refresh(lead)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Lead update conflicts with existing data")

    return lead


@router.delete("/{lead_id}")
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    lead = db.get(Lead, lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    db.delete(lead)
    db.commit()

    return {"message": "Lead deleted successfully"}
