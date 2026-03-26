from datetime import date

from sqlmodel import Session, select

from app.config import get_settings
from app.models.entities import EPS, Institucion, InstitucionEPS, Paciente, Provider, Specialty


def seed_initial_data(session: Session) -> None:
    _seed_eps_ips_pacientes(session)
    _seed_providers_and_specialties(session)


def _seed_eps_ips_pacientes(session: Session) -> None:
    settings = get_settings()

    eps_seed = [
        ("EPS-SAN", "EPS Sanitas"),
        ("EPS-NUE", "Nueva EPS"),
        ("EPS-SLT", "Salud Total"),
        (settings.eps_code, settings.eps_name),
    ]

    for codigo, nombre in eps_seed:
        existing = session.exec(select(EPS).where(EPS.codigo == codigo)).first()
        if existing is None:
            session.add(EPS(nombre=nombre, codigo=codigo, estado="activo"))
    session.commit()

    eps_rows = session.exec(select(EPS)).all()
    eps_by_code = {row.codigo: row for row in eps_rows}

    institucion_seed = [
        {
            "nombre": "Clinica Central Norte",
            "nit": "900100100-1",
            "direccion": "Cra 15 # 88-10, Bogota",
            "telefono": "6017001001",
            "estado": "activo",
        },
        {
            "nombre": "IPS Familiar Occidente",
            "nit": "900200200-2",
            "direccion": "Av 68 # 24-30, Bogota",
            "telefono": "6017002002",
            "estado": "activo",
        },
        {
            "nombre": "Centro Medico Sur",
            "nit": "900300300-3",
            "direccion": "Calle 45 # 12-40, Cali",
            "telefono": "6026003003",
            "estado": "activo",
        },
        {
            "nombre": "Unidad Integral del Caribe",
            "nit": "900400400-4",
            "direccion": "Cra 51B # 79-20, Barranquilla",
            "telefono": "6055004004",
            "estado": "activo",
        },
    ]

    for payload in institucion_seed:
        existing = session.exec(select(Institucion).where(Institucion.nit == payload["nit"])).first()
        if existing is None:
            session.add(Institucion(**payload))
    session.commit()

    instituciones = session.exec(select(Institucion)).all()
    ips_by_nit = {row.nit: row for row in instituciones}

    principal_code = settings.eps_code
    secondary_code = "EPS-NUE" if principal_code != "EPS-NUE" else "EPS-SAN"

    links = [
        ("900100100-1", principal_code, "Red primaria de atencion"),
        ("900200200-2", principal_code, "Convenio para consulta externa"),
        ("900300300-3", secondary_code, "Convenio especializado"),
        ("900400400-4", "EPS-SLT", "Cobertura regional"),
    ]

    for nit, eps_code, observaciones in links:
        institucion = ips_by_nit.get(nit)
        eps = eps_by_code.get(eps_code)
        if institucion is None or eps is None:
            continue
        existing = session.exec(
            select(InstitucionEPS).where(
                InstitucionEPS.id_institucion == institucion.id_institucion,
                InstitucionEPS.id_eps == eps.id_eps,
            )
        ).first()
        if existing is None:
            session.add(
                InstitucionEPS(
                    id_institucion=institucion.id_institucion,
                    id_eps=eps.id_eps,
                    observaciones=observaciones,
                )
            )
    session.commit()

    pacientes_seed = [
        {
            "tipo_documento": "CC",
            "numero_documento": "1002003001",
            "nombres": "Juan",
            "apellidos": "Perez",
            "fecha_nacimiento": date(1990, 3, 12),
            "telefono": "3001112233",
            "correo": "juan.perez@example.com",
            "estado": "activo",
            "nit_institucion": "900100100-1",
        },
        {
            "tipo_documento": "CC",
            "numero_documento": "1002003002",
            "nombres": "Maria",
            "apellidos": "Lopez",
            "fecha_nacimiento": date(1988, 7, 2),
            "telefono": "3004445566",
            "correo": "maria.lopez@example.com",
            "estado": "activo",
            "nit_institucion": "900200200-2",
        },
        {
            "tipo_documento": "TI",
            "numero_documento": "9001002003",
            "nombres": "Andres",
            "apellidos": "Gomez",
            "fecha_nacimiento": date(2007, 11, 20),
            "telefono": "3112223344",
            "correo": "andres.gomez@example.com",
            "estado": "activo",
            "nit_institucion": "900300300-3",
        },
        {
            "tipo_documento": "CE",
            "numero_documento": "X12345678",
            "nombres": "Elena",
            "apellidos": "Torres",
            "fecha_nacimiento": date(1995, 1, 28),
            "telefono": "3128887766",
            "correo": "elena.torres@example.com",
            "estado": "activo",
            "nit_institucion": "900400400-4",
        },
    ]

    for payload in pacientes_seed:
        existing = session.exec(
            select(Paciente).where(
                Paciente.tipo_documento == payload["tipo_documento"],
                Paciente.numero_documento == payload["numero_documento"],
            )
        ).first()
        if existing is not None:
            continue

        institucion = ips_by_nit.get(payload["nit_institucion"])
        if institucion is None:
            continue

        session.add(
            Paciente(
                tipo_documento=payload["tipo_documento"],
                numero_documento=payload["numero_documento"],
                nombres=payload["nombres"],
                apellidos=payload["apellidos"],
                fecha_nacimiento=payload["fecha_nacimiento"],
                telefono=payload["telefono"],
                correo=payload["correo"],
                estado=payload["estado"],
                id_institucion=institucion.id_institucion,
            )
        )
    session.commit()


def _seed_providers_and_specialties(session: Session) -> None:
    has_specialties = session.exec(select(Specialty)).first() is not None
    if not has_specialties:
        specialties = [
            Specialty(name="Medicina General"),
            Specialty(name="Pediatria"),
            Specialty(name="Odontologia"),
            Specialty(name="Ginecologia"),
        ]
        for specialty in specialties:
            session.add(specialty)
        session.commit()

    has_providers = session.exec(select(Provider)).first() is not None
    if has_providers:
        return

    persisted_specialties = session.exec(select(Specialty).order_by(Specialty.id)).all()

    providers = [
        Provider(full_name="Dra. Ana Martinez", specialty_id=persisted_specialties[0].id),
        Provider(full_name="Dr. Carlos Perez", specialty_id=persisted_specialties[1].id),
        Provider(full_name="Dra. Laura Gomez", specialty_id=persisted_specialties[2].id),
        Provider(full_name="Dr. Jorge Ramirez", specialty_id=persisted_specialties[3].id),
        Provider(full_name="Dra. Sofia Lopez", specialty_id=persisted_specialties[0].id),
    ]
    for provider in providers:
        session.add(provider)
    session.commit()
