"""HEI registry API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.hei import (
    FacultyCapabilityCreate, FacultyCapabilityResponse, FacultyCapabilityUpdate,
    FacultyCreate, FacultyResponse, FacultyUpdate,
    HeiCapabilityCreate, HeiCapabilityResponse, HeiCapabilityUpdate,
    HeiCreate, HeiResponse, HeiUpdate,
    ResourceCapabilityCreate, ResourceCapabilityResponse, ResourceCapabilityUpdate,
    ResourceCreate, ResourceResponse, ResourceUpdate,
)
from app.services.hei import (
    add_faculty_capability, add_hei_capability, add_resource_capability,
    create_faculty, create_hei, create_resource,
    get_faculty, get_faculty_capabilities, get_faculty_list,
    get_hei, get_hei_capabilities, get_heis,
    get_resource, get_resource_capabilities, get_resources,
    update_faculty, update_faculty_capability,
    update_hei, update_hei_capability,
    update_resource, update_resource_capability,
)

router = APIRouter(tags=["hei"])

DB  = Annotated[Session, Depends(get_db)]
CU  = Annotated[User, Depends(get_current_user)]


# ── HEI Profile ────────────────────────────────────────────────────────────────

@router.post("/api/heis", response_model=HeiResponse, status_code=201, summary="Create HEI profile")
def create_hei_route(payload: HeiCreate, db: DB, current_user: CU) -> HeiResponse:
    """Create an HEI profile. Organization must be of type HEI."""
    return create_hei(db, payload, current_user)


@router.get("/api/heis", response_model=list[HeiResponse], summary="List all HEI profiles")
def list_heis(db: DB, _: CU) -> list[HeiResponse]:
    return get_heis(db)


@router.get("/api/heis/{hei_id}", response_model=HeiResponse, summary="Get HEI profile by ID")
def get_hei_route(hei_id: UUID, db: DB, _: CU) -> HeiResponse:
    return get_hei(db, hei_id)


@router.put("/api/heis/{hei_id}", response_model=HeiResponse, summary="Update HEI profile")
def update_hei_route(hei_id: UUID, payload: HeiUpdate, db: DB, current_user: CU) -> HeiResponse:
    return update_hei(db, hei_id, payload, current_user)


# ── HEI Capabilities ──────────────────────────────────────────────────────────

@router.post("/api/heis/{hei_id}/capabilities", response_model=HeiCapabilityResponse,
             status_code=201, summary="Add capability to HEI")
def add_hei_cap(hei_id: UUID, payload: HeiCapabilityCreate, db: DB, current_user: CU) -> HeiCapabilityResponse:
    return add_hei_capability(db, hei_id, payload, current_user)


@router.get("/api/heis/{hei_id}/capabilities", response_model=list[HeiCapabilityResponse],
            summary="List HEI capabilities")
def list_hei_caps(hei_id: UUID, db: DB, _: CU) -> list[HeiCapabilityResponse]:
    return get_hei_capabilities(db, hei_id)


@router.put("/api/heis/{hei_id}/capabilities/{hei_capability_id}",
            response_model=HeiCapabilityResponse, summary="Update HEI capability")
def update_hei_cap(hei_id: UUID, hei_capability_id: UUID, payload: HeiCapabilityUpdate,
                   db: DB, current_user: CU) -> HeiCapabilityResponse:
    return update_hei_capability(db, hei_id, hei_capability_id, payload, current_user)


# ── Faculty ────────────────────────────────────────────────────────────────────

@router.post("/api/heis/{hei_id}/faculty", response_model=FacultyResponse,
             status_code=201, summary="Add faculty to HEI")
def create_faculty_route(hei_id: UUID, payload: FacultyCreate, db: DB, current_user: CU) -> FacultyResponse:
    return create_faculty(db, hei_id, payload, current_user)


@router.get("/api/heis/{hei_id}/faculty", response_model=list[FacultyResponse],
            summary="List faculty in an HEI")
def list_faculty(hei_id: UUID, db: DB, _: CU) -> list[FacultyResponse]:
    return get_faculty_list(db, hei_id)


@router.get("/api/faculty/{faculty_id}", response_model=FacultyResponse,
            summary="Get faculty profile by ID")
def get_faculty_route(faculty_id: UUID, db: DB, _: CU) -> FacultyResponse:
    return get_faculty(db, faculty_id)


@router.put("/api/faculty/{faculty_id}", response_model=FacultyResponse,
            summary="Update faculty profile")
def update_faculty_route(faculty_id: UUID, payload: FacultyUpdate, db: DB, current_user: CU) -> FacultyResponse:
    return update_faculty(db, faculty_id, payload, current_user)


# ── Faculty Capabilities ──────────────────────────────────────────────────────

@router.post("/api/faculty/{faculty_id}/capabilities",
             response_model=FacultyCapabilityResponse, status_code=201,
             summary="Add capability to faculty")
def add_faculty_cap(faculty_id: UUID, payload: FacultyCapabilityCreate, db: DB, current_user: CU) -> FacultyCapabilityResponse:
    return add_faculty_capability(db, faculty_id, payload, current_user)


@router.get("/api/faculty/{faculty_id}/capabilities",
            response_model=list[FacultyCapabilityResponse],
            summary="List faculty capabilities")
def list_faculty_caps(faculty_id: UUID, db: DB, _: CU) -> list[FacultyCapabilityResponse]:
    return get_faculty_capabilities(db, faculty_id)


@router.put("/api/faculty/{faculty_id}/capabilities/{faculty_capability_id}",
            response_model=FacultyCapabilityResponse, summary="Update faculty capability")
def update_faculty_cap(faculty_id: UUID, faculty_capability_id: UUID,
                       payload: FacultyCapabilityUpdate, db: DB, current_user: CU) -> FacultyCapabilityResponse:
    return update_faculty_capability(db, faculty_id, faculty_capability_id, payload, current_user)


# ── Institutional Resources ────────────────────────────────────────────────────

@router.post("/api/heis/{hei_id}/resources", response_model=ResourceResponse,
             status_code=201, summary="Add resource to HEI")
def create_resource_route(hei_id: UUID, payload: ResourceCreate, db: DB, current_user: CU) -> ResourceResponse:
    return create_resource(db, hei_id, payload, current_user)


@router.get("/api/heis/{hei_id}/resources", response_model=list[ResourceResponse],
            summary="List HEI resources")
def list_resources(hei_id: UUID, db: DB, _: CU) -> list[ResourceResponse]:
    return get_resources(db, hei_id)


@router.get("/api/resources/{resource_id}", response_model=ResourceResponse,
            summary="Get resource by ID")
def get_resource_route(resource_id: UUID, db: DB, _: CU) -> ResourceResponse:
    return get_resource(db, resource_id)


@router.put("/api/resources/{resource_id}", response_model=ResourceResponse,
            summary="Update resource")
def update_resource_route(resource_id: UUID, payload: ResourceUpdate, db: DB, current_user: CU) -> ResourceResponse:
    return update_resource(db, resource_id, payload, current_user)


# ── Resource Capabilities ──────────────────────────────────────────────────────

@router.post("/api/resources/{resource_id}/capabilities",
             response_model=ResourceCapabilityResponse, status_code=201,
             summary="Add capability to resource")
def add_resource_cap(resource_id: UUID, payload: ResourceCapabilityCreate, db: DB, current_user: CU) -> ResourceCapabilityResponse:
    return add_resource_capability(db, resource_id, payload, current_user)


@router.get("/api/resources/{resource_id}/capabilities",
            response_model=list[ResourceCapabilityResponse],
            summary="List resource capabilities")
def list_resource_caps(resource_id: UUID, db: DB, _: CU) -> list[ResourceCapabilityResponse]:
    return get_resource_capabilities(db, resource_id)


@router.put("/api/resources/{resource_id}/capabilities/{resource_capability_id}",
            response_model=ResourceCapabilityResponse, summary="Update resource capability")
def update_resource_cap(resource_id: UUID, resource_capability_id: UUID,
                        payload: ResourceCapabilityUpdate, db: DB, current_user: CU) -> ResourceCapabilityResponse:
    return update_resource_capability(db, resource_id, resource_capability_id, payload, current_user)
