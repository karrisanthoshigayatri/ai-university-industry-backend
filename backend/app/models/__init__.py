"""SQLAlchemy models used by the application."""

from app.models.organization import Organization
from app.models.government_profile import GovernmentProfile
from app.models.user import User
from app.models.problem import Problem, ProblemEvidence, ProblemRelation
from app.models.validation import Validation
from app.models.capability import Capability, CapabilityTaxonomy
from app.models.ai_analysis import (
    ProblemCategory,
    ProblemPriority,
    ProblemRequirementCapability,
    ProblemRequirementProfile,
)
from app.models.hei import (
    FacultyExpertCapability,
    FacultyExpertProfile,
    HeiCapability,
    HeiProfile,
    InstitutionalResource,
    ResourceCapability,
)
from app.models.evidence import (
    Availability,
    CapabilityEvidence,
    EntityConstraint,
)
from app.models.partner import (
    PartnerCapability,
    PartnerProfile,
    PartnerSupportOffering,
)
from app.models.matching import HeiMatch
from app.models.faculty_resource_match import FacultyResourceMatch
from app.models.project import Project, ProjectCapability, ProjectResource, ProjectTeam, ProjectTeamMember
from app.models.capability_gap import CapabilityGap, PartnerMatch

__all__ = [
    "Availability",
    "Capability",
    "CapabilityEvidence",
    "CapabilityTaxonomy",
    "EntityConstraint",
    "FacultyExpertCapability",
    "FacultyExpertProfile",
    "GovernmentProfile",
    "CapabilityGap",
    "FacultyResourceMatch",
    "HeiCapability",
    "HeiMatch",
    "HeiProfile",
    "InstitutionalResource",
    "Organization",
    "PartnerCapability",
    "PartnerProfile",
    "PartnerSupportOffering",
    "Problem",
    "Project",
    "ProjectCapability",
    "ProjectResource",
    "ProjectTeam",
    "ProjectTeamMember",
    "ProblemCategory",
    "ProblemEvidence",
    "ProblemPriority",
    "ProblemRelation",
    "ProblemRequirementCapability",
    "ProblemRequirementProfile",
    "ResourceCapability",
    "User",
    "Validation",
]
