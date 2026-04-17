from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import Settings, get_settings
from app.services.fhir import operation_outcome

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class SmartAuthContext:
    subject: str
    patient_id: str | None
    scopes: frozenset[str]
    claims: dict[str, Any]


def build_smart_configuration(settings: Settings) -> dict[str, Any]:
    base_auth_url = settings.supabase_url.rstrip("/")
    issuer = settings.smart_issuer or f"{base_auth_url}/auth/v1"
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{base_auth_url}/auth/v1/authorize",
        "token_endpoint": f"{base_auth_url}/auth/v1/token",
        "jwks_uri": f"{base_auth_url}/auth/v1/.well-known/jwks.json",
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "response_types_supported": ["code"],
        "capabilities": [
            "launch-standalone",
            "client-public",
            "permission-patient",
        ],
        "scopes_supported": [
            "openid",
            "profile",
            "offline_access",
            "patient/Slot.read",
            "patient/Appointment.read",
            "patient/Appointment.write",
        ],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
    }


def require_smart_access(
    resource_type: str,
    access_type: str,
    *,
    patient_resolver: Callable[[Request], str | None] | None = None,
) -> Callable[..., SmartAuthContext]:
    async def dependency(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    ) -> SmartAuthContext:
        token = _extract_bearer_token(credentials)
        context = validate_smart_token(token=token)

        expected_scope = f"patient/{resource_type}.{access_type}"
        if not _has_scope(context.scopes, expected_scope):
            raise _forbidden(
                f"Faltan privilegios para {expected_scope}",
            )

        if patient_resolver is not None:
            if getattr(request.state, "_smart_cached_json", None) is None:
                try:
                    request.state._smart_cached_json = await request.json()
                except Exception:
                    request.state._smart_cached_json = {}
            resource_patient_id = patient_resolver(request)
            if resource_patient_id is None:
                raise _forbidden("No fue posible determinar el paciente del recurso")
            if context.patient_id is None:
                raise _forbidden("El token no contiene contexto de paciente")
            if str(context.patient_id) != str(resource_patient_id):
                raise _forbidden("El paciente del token no coincide con el recurso solicitado")

        request.state.smart_auth = context
        return context

    return dependency


def validate_smart_token(token: str, settings: Settings | None = None) -> SmartAuthContext:
    resolved_settings = settings or get_settings()
    claims = _decode_token(token=token, settings=resolved_settings)
    scopes = _extract_scopes(claims)
    subject = str(claims.get("sub") or "")
    if not subject:
        raise _unauthorized("Token SMART inválido: falta claim sub")

    patient_claim_name = resolved_settings.smart_patient_claim
    patient_id = claims.get(patient_claim_name) or claims.get("patient") or claims.get("patient_id")
    return SmartAuthContext(
        subject=subject,
        patient_id=str(patient_id) if patient_id is not None else None,
        scopes=frozenset(scopes),
        claims=claims,
    )


def resolve_patient_id_from_appointment_request(request: Request) -> str | None:
    body = getattr(request.state, "_smart_cached_json", None)
    if body is None:
        return None
    for participant in body.get("participant", []):
        actor = participant.get("actor") or {}
        reference = str(actor.get("reference") or "")
        if reference.startswith("Patient/"):
            return reference.split("/", 1)[1]
    return None


async def cache_request_json(request: Request) -> None:
    if getattr(request.state, "_smart_cached_json", None) is None:
        try:
            request.state._smart_cached_json = await request.json()
        except Exception:
            request.state._smart_cached_json = {}


def _decode_token(token: str, settings: Settings) -> dict[str, Any]:
    issuer = settings.smart_issuer or f"{settings.supabase_url.rstrip('/')}/auth/v1"
    audience = settings.smart_audience
    options = {"verify_aud": audience is not None, "verify_iss": issuer is not None}

    try:
        if settings.supabase_jwt_secret:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=audience,
                issuer=issuer,
                options=options,
            )

        jwk_client = _jwk_client(settings.supabase_url)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=audience,
            issuer=issuer,
            options=options,
        )
    except (jwt.InvalidTokenError, httpx.HTTPError) as exc:
        raise _unauthorized("Token SMART inválido o expirado") from exc


@lru_cache(maxsize=8)
def _jwk_client(supabase_url: str) -> PyJWKClient:
    jwks_uri = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_uri)


def _extract_scopes(claims: dict[str, Any]) -> set[str]:
    scope_claim = claims.get("scope")
    scp_claim = claims.get("scp")
    scopes: set[str] = set()
    if isinstance(scope_claim, str):
        scopes.update(part for part in scope_claim.split(" ") if part)
    if isinstance(scp_claim, str):
        scopes.update(part for part in scp_claim.split(" ") if part)
    if isinstance(scp_claim, list):
        scopes.update(str(part) for part in scp_claim if part)
    return scopes


def _has_scope(scopes: frozenset[str], expected_scope: str) -> bool:
    if expected_scope in scopes:
        return True
    compartment, rest = expected_scope.split("/", 1)
    resource, action = rest.split(".", 1)
    return (
        f"{compartment}/*.{action}" in scopes
        or f"{compartment}/{resource}.*" in scopes
        or f"{compartment}/*.*" in scopes
    )


def _extract_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise _unauthorized("Token SMART Bearer requerido")
    return credentials.credentials.strip()


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=operation_outcome("login", message))


def _forbidden(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=operation_outcome("forbidden", message))
