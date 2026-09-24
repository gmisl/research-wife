"""Rule-based validation before a candidate can enter the verified dataset."""

from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass
class Candidate:
    name: str
    country_code: str
    product_family: str
    product_category: str
    product_text: str = ''
    website: str = ''
    official_email: str = ''
    official_phone: str = ''
    supplier_type: str = ''
    organic_certification_body: str = ''
    certificate_number: str = ''
    certification_source_url: str = ''
    wholesale_evidence: str = ''
    frozen: bool = False
    price_is_retail: bool = False


@dataclass
class ValidationResult:
    status: str
    priority_class: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_candidate(candidate: Candidate) -> ValidationResult:
    reasons: list[str] = []
    warnings: list[str] = []
    text = ' '.join([
        candidate.product_text,
        candidate.product_category,
        candidate.wholesale_evidence,
    ]).lower()

    if candidate.product_family not in {'beef', 'chicken'}:
        reasons.append('unsupported_product_family')
    if not candidate.country_code or len(candidate.country_code) != 2:
        reasons.append('invalid_eu_country_code')
    if not candidate.name.strip():
        reasons.append('missing_company_name')
    if not candidate.website and not candidate.official_email and not candidate.official_phone:
        reasons.append('missing_official_contact')
    if candidate.price_is_retail:
        reasons.append('retail_only')
    if not candidate.frozen:
        reasons.append('frozen_product_not_proven')
    if not candidate.organic_certification_body:
        reasons.append('organic_certification_missing')
    if not candidate.certificate_number and not candidate.certification_source_url:
        reasons.append('organic_certificate_evidence_missing')
    if not candidate.wholesale_evidence.strip():
        reasons.append('wholesale_evidence_missing')
    else:
        if not re.search(r'\b(pallet|bulk|moq|minimum|tonne|ton|kg|industrial|wholesale)\b', candidate.wholesale_evidence.lower()):
            warnings.append('wholesale_evidence_is_weak')
    if candidate.supplier_type in {'distributor', 'wholesaler', 'exporter'}:
        warnings.append('secondary_supplier_not_primary_producer')

    if reasons:
        status = 'rejected' if any(x in reasons for x in ('retail_only', 'unsupported_product_family')) else 'unverified'
    else:
        status = 'active'
    priority = 'secondary' if candidate.supplier_type in {'distributor', 'wholesaler', 'exporter'} else 'primary'
    return ValidationResult(status=status, priority_class=priority, reasons=reasons, warnings=warnings)
