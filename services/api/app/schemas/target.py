"""Quantum Flow Technologies — Target API Schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TargetCreate(BaseModel):
    """Payload for registering a new domain target."""

    hostname: str = Field(
        ...,
        description="Target domain name to inspect (e.g. example.com)",
        examples=["example.com"],
    )
    display_name: str | None = Field(
        default=None,
        max_length=255,
        description="Optional human-readable label",
    )
    description: str | None = Field(
        default=None,
        description="Optional description or operational context",
    )
    authorisation_declared: bool = Field(
        default=False,
        description="Explicit declaration that user has authorized permission to scan this domain",
    )
    explicit_authorisation_confirmed: bool | None = Field(
        default=None,
        description="Alias for authorisation_declared for frontend compatibility",
    )
    authorised_by: str | None = Field(
        default=None,
        max_length=255,
        description="Identifier of authorizing person or service",
    )
    authorisation_reference: str | None = Field(
        default=None,
        max_length=255,
        description="Ticket ID, compliance reference, or authorization document identifier",
    )
    environment: str | None = Field(
        default=None,
        description="Optional deployment environment",
    )
    criticality: str | None = Field(
        default=None,
        description="Optional asset criticality",
    )

    @model_validator(mode="after")
    def sync_authorisation(self) -> "TargetCreate":
        if self.explicit_authorisation_confirmed is not None:
            self.authorisation_declared = (
                self.authorisation_declared or self.explicit_authorisation_confirmed
            )
        return self


class TargetUpdate(BaseModel):
    """Payload for updating target metadata."""

    display_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)


class TargetVerifyRequest(BaseModel):
    """Payload for verifying target ownership or control."""

    verification_method: str = Field(
        default="token",
        description="Method used for verification (e.g. 'token', 'dns_txt')",
    )
    token: str | None = Field(
        default=None,
        description="Verification challenge token matching target.verification_token",
    )


class TargetResponse(BaseModel):
    """Response model representing a registered domain target."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hostname: str
    display_name: str | None
    description: str | None
    status: str
    authorisation_status: str
    authorised_by: str | None
    authorisation_reference: str | None
    verification_token: str
    verified_at: datetime | None
    disabled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    is_eligible_for_scan: bool


class TargetListResponse(BaseModel):
    """Paginated collection of domain targets."""

    items: list[TargetResponse]
    total: int
    skip: int
    limit: int
