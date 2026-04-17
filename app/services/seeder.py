from datetime import date, datetime, time, timedelta

from sqlmodel import Session, select

from app.config import get_settings
from app.models.entities import Appointment, IPS, Paciente, Provider, Specialty

SPECIALTY_REPS_CODES = {
    "medicina general": "101",
    "pediatria": "335",
    "cardiologia": "302",
    "ginecobstetricia": "318",
    "dermatologia": "312",
    "neurologia": "329",
    "ortopedia": "331",
    "oftalmologia": "330",
    "psicologia": "342",
    "gastroenterologia": "315",
}

INSTITUTION_CATALOG = {
    "IPS-FSF": {
        "nombre": "Fundación Santa Fe de Bogotá",
        "nit": "860032640-1",
        "direccion": "Calle 119 # 7-75",
        "telefono": None,
        "estado": "ACTIVO",
    },
    "IPS-CLY": {
        "nombre": "Clínica Country",
        "nit": "860010958-3",
        "direccion": "Carrera 16 # 82-57",
        "telefono": None,
        "estado": "ACTIVO",
    },
    "IPS-CUC": {
        "nombre": "Clínica Universitaria Colombia",
        "nit": "900073809-1",
        "direccion": "Calle 22 Bis # 66-46",
        "telefono": None,
        "estado": "ACTIVO",
    },
    "IPS-HSI": {
        "nombre": "Hospital Universitario San Ignacio",
        "nit": "860016693-2",
        "direccion": "Carrera 7 # 40-62",
        "telefono": None,
        "estado": "ACTIVO",
    },
    "IPS-MED": {
        "nombre": "Hospital Universitario Mayor - Méderi",
        "nit": "900203716-1",
        "direccion": "Calle 24 # 29-45",
        "telefono": None,
        "estado": "ACTIVO",
    },
}


def seed_initial_data(session: Session) -> None:
    settings = get_settings()
    dataset = _dataset_for_ips(settings.ips_code)

    _seed_ips(session)
    _seed_pacientes(session, dataset["pacientes"])
    specialty_by_name = _seed_especialidades(session, dataset["especialidades"])
    _seed_prestadores(session, specialty_by_name, dataset["prestadores"])
    _seed_demo_appointment(session)


def _seed_ips(session: Session) -> None:
    settings = get_settings()
    existing = session.exec(select(IPS).where(IPS.nit == settings.ips_nit)).first()
    if existing is not None:
        return

    institution = INSTITUTION_CATALOG.get(settings.ips_code, {})

    session.add(
        IPS(
            nombre=institution.get("nombre", settings.ips_name),
            codigo=settings.ips_code,
            nit=institution.get("nit", settings.ips_nit),
            direccion=institution.get("direccion"),
            telefono=institution.get("telefono"),
            estado=institution.get("estado", "ACTIVO"),
        )
    )
    session.commit()


def _seed_pacientes(session: Session, pacientes_seed: list[dict]) -> None:
    for payload in pacientes_seed:
        existing = session.exec(
            select(Paciente).where(
                Paciente.tipo_documento == payload["tipo_documento"],
                Paciente.numero_documento == payload["numero_documento"],
            )
        ).first()
        if existing is not None:
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
                estado="activo",
            )
        )
    session.commit()


def _seed_especialidades(session: Session, specialties_seed: list[str]) -> dict[str, int]:
    for specialty_name in specialties_seed:
        existing = session.exec(select(Specialty).where(Specialty.name == specialty_name)).first()
        if existing is None:
            session.add(
                Specialty(
                    name=specialty_name,
                    codigo_reps=SPECIALTY_REPS_CODES.get(_normalize_specialty_name(specialty_name)),
                )
            )
    session.commit()

    specialties = session.exec(select(Specialty)).all()
    return {item.name: item.id for item in specialties}


def _normalize_specialty_name(value: str) -> str:
    replacements = str.maketrans(
        {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
        }
    )
    return str(value or "").strip().lower().translate(replacements)


def _seed_prestadores(session: Session, specialty_by_name: dict[str, int], providers_seed: list[dict]) -> None:
    for payload in providers_seed:
        specialty_id = specialty_by_name.get(payload["especialidad"])
        if specialty_id is None:
            continue

        existing = session.exec(select(Provider).where(Provider.full_name == payload["nombre_completo"])).first()
        if existing is not None:
            continue

        session.add(Provider(full_name=payload["nombre_completo"], specialty_id=specialty_id))
    session.commit()


def _seed_demo_appointment(session: Session) -> None:
    already_exists = session.exec(select(Appointment)).first()
    if already_exists is not None:
        return

    patient = session.exec(select(Paciente).order_by(Paciente.id_paciente)).first()
    provider = session.exec(select(Provider).order_by(Provider.id)).first()
    if patient is None or provider is None:
        return

    slot_start = _next_business_day_slot()
    session.add(
        Appointment(
            patient_id=patient.id_paciente,
            provider_id=provider.id,
            specialty_id=provider.specialty_id,
            slot_start=slot_start,
            status="scheduled",
        )
    )
    session.commit()


def _next_business_day_slot() -> datetime:
    target = date.today() + timedelta(days=1)
    while target.weekday() >= 5:
        target += timedelta(days=1)
    return datetime.combine(target, time(8, 0))


def _dataset_for_ips(ips_code: str) -> dict:
    defaults = {
        "pacientes": [
            {
                "tipo_documento": "CC",
                "numero_documento": "1099001001",
                "nombres": "Samuel",
                "apellidos": "Rios",
                "fecha_nacimiento": date(1992, 9, 18),
                "telefono": "3001110001",
                "correo": "samuel.rios@example.com",
            },
            {
                "tipo_documento": "CC",
                "numero_documento": "1099001002",
                "nombres": "Carolina",
                "apellidos": "Vargas",
                "fecha_nacimiento": date(1989, 2, 7),
                "telefono": "3001110002",
                "correo": "carolina.vargas@example.com",
            },
        ],
        "especialidades": [
            "Medicina General",
            "Pediatría",
            "Ginecobstetricia",
            "Dermatología",
        ],
        "prestadores": [
            {"nombre_completo": "Dra. Luciana Suarez", "especialidad": "Medicina General"},
            {"nombre_completo": "Dr. Mateo Cardenas", "especialidad": "Pediatría"},
            {"nombre_completo": "Dra. Diana Bernal", "especialidad": "Ginecobstetricia"},
            {"nombre_completo": "Dr. Felipe Neira", "especialidad": "Dermatología"},
        ],
    }

    by_ips = {
        "IPS-FSF": {
            "pacientes": [
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1014977178",
                    "nombres": "Adrian",
                    "apellidos": "Ruiz",
                    "fecha_nacimiento": date(2004, 8, 2),
                    "telefono": "573182273533",
                    "correo": "adrianrrruiz@gmail.com",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1100101101",
                    "nombres": "Julian",
                    "apellidos": "Arenas",
                    "fecha_nacimiento": date(1991, 4, 11),
                    "telefono": "3015001101",
                    "correo": "julian.arenas@fsf.mock",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1100101102",
                    "nombres": "Valentina",
                    "apellidos": "Pardo",
                    "fecha_nacimiento": date(1986, 10, 3),
                    "telefono": "3015001102",
                    "correo": "valentina.pardo@fsf.mock",
                },
                {
                    "tipo_documento": "TI",
                    "numero_documento": "1002003011",
                    "nombres": "Camilo",
                    "apellidos": "Arias",
                    "fecha_nacimiento": date(2008, 5, 22),
                    "telefono": "3015001103",
                    "correo": "camilo.arias@fsf.mock",
                },
            ],
            "especialidades": [
                "Medicina General",
                "Pediatría",
                "Cardiología",
                "Ginecobstetricia",
                "Dermatología",
                "Neurología",
                "Ortopedia",
                "Oftalmología",
                "Psicología",
                "Gastroenterología",
            ],
            "prestadores": [
                {"nombre_completo": "Dra. Paula Restrepo", "especialidad": "Medicina General"},
                {"nombre_completo": "Dr. Tomas Rojas", "especialidad": "Pediatría"},
                {"nombre_completo": "Dr. Nicolas Padilla", "especialidad": "Cardiología"},
                {"nombre_completo": "Dra. Diana Bernal", "especialidad": "Ginecobstetricia"},
                {"nombre_completo": "Dr. Felipe Neira", "especialidad": "Dermatología"},
                {"nombre_completo": "Dra. Marcela Torres", "especialidad": "Neurología"},
                {"nombre_completo": "Dr. Luis Fontalvo", "especialidad": "Ortopedia"},
                {"nombre_completo": "Dra. Sandra Molina", "especialidad": "Oftalmología"},
                {"nombre_completo": "Dra. Johana Cotes", "especialidad": "Psicología"},
                {"nombre_completo": "Dr. Julian Acosta", "especialidad": "Gastroenterología"},
            ],
        },
        "IPS-CLY": {
            "pacientes": [
                {
                    "tipo_documento": "CE",
                    "numero_documento": "485101",
                    "nombres": "Leo",
                    "apellidos": "Velazquez",
                    "fecha_nacimiento": date(2026, 4, 2),
                    "telefono": "+573208761377",
                    "correo": "levelazquez@javeriana.edu.co",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1200202201",
                    "nombres": "Daniela",
                    "apellidos": "Mina",
                    "fecha_nacimiento": date(1993, 6, 14),
                    "telefono": "3026002201",
                    "correo": "daniela.mina@cly.mock",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1200202202",
                    "nombres": "Ricardo",
                    "apellidos": "Sierra",
                    "fecha_nacimiento": date(1984, 12, 30),
                    "telefono": "3026002202",
                    "correo": "ricardo.sierra@cly.mock",
                },
                {
                    "tipo_documento": "CE",
                    "numero_documento": "Y90022003",
                    "nombres": "Natalia",
                    "apellidos": "Duarte",
                    "fecha_nacimiento": date(1997, 8, 4),
                    "telefono": "3026002203",
                    "correo": "natalia.duarte@cly.mock",
                },
            ],
            "especialidades": [
                "Pediatría",
                "Cardiología",
                "Ginecobstetricia",
                "Dermatología",
                "Ortopedia",
                "Gastroenterología",
            ],
            "prestadores": [
                {"nombre_completo": "Dr. Tomas Rojas", "especialidad": "Pediatría"},
                {"nombre_completo": "Dr. Nicolas Padilla", "especialidad": "Cardiología"},
                {"nombre_completo": "Dra. Laura Salcedo", "especialidad": "Ginecobstetricia"},
                {"nombre_completo": "Dr. Felipe Neira", "especialidad": "Dermatología"},
                {"nombre_completo": "Dr. Luis Fontalvo", "especialidad": "Ortopedia"},
                {"nombre_completo": "Dr. Julian Acosta", "especialidad": "Gastroenterología"},
            ],
        },
        "IPS-CUC": {
            "pacientes": [
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1400404401",
                    "nombres": "Laura",
                    "apellidos": "Castro",
                    "fecha_nacimiento": date(1990, 3, 18),
                    "telefono": "3048004401",
                    "correo": "laura.castro@cuc.mock",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1400404402",
                    "nombres": "Andres",
                    "apellidos": "Morales",
                    "fecha_nacimiento": date(1988, 7, 5),
                    "telefono": "3048004402",
                    "correo": "andres.morales@cuc.mock",
                },
                {
                    "tipo_documento": "TI",
                    "numero_documento": "1040404411",
                    "nombres": "Sara",
                    "apellidos": "Prieto",
                    "fecha_nacimiento": date(2010, 1, 12),
                    "telefono": "3048004403",
                    "correo": "sara.prieto@cuc.mock",
                },
            ],
            "especialidades": [
                "Medicina General",
                "Pediatría",
                "Neurología",
                "Oftalmología",
                "Gastroenterología",
            ],
            "prestadores": [
                {"nombre_completo": "Dra. Luciana Suarez", "especialidad": "Medicina General"},
                {"nombre_completo": "Dr. Mateo Cardenas", "especialidad": "Pediatría"},
                {"nombre_completo": "Dra. Marcela Torres", "especialidad": "Neurología"},
                {"nombre_completo": "Dra. Sandra Molina", "especialidad": "Oftalmología"},
                {"nombre_completo": "Dr. Julian Acosta", "especialidad": "Gastroenterología"},
            ],
        },
        "IPS-HSI": {
            "pacientes": [
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1014977178",
                    "nombres": "Adrian",
                    "apellidos": "Ruiz",
                    "fecha_nacimiento": date(2004, 8, 2),
                    "telefono": "573182273533",
                    "correo": "adrianrrruiz@gmail.com",
                },
                {
                    "tipo_documento": "CE",
                    "numero_documento": "485101",
                    "nombres": "Leo",
                    "apellidos": "Velazquez",
                    "fecha_nacimiento": date(2026, 4, 2),
                    "telefono": "+573208761377",
                    "correo": "levelazquez@javeriana.edu.co",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1300303301",
                    "nombres": "Kevin",
                    "apellidos": "Barrios",
                    "fecha_nacimiento": date(1994, 1, 9),
                    "telefono": "3037003301",
                    "correo": "kevin.barrios@hsi.mock",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1300303302",
                    "nombres": "Paola",
                    "apellidos": "Vergara",
                    "fecha_nacimiento": date(1987, 11, 19),
                    "telefono": "3037003302",
                    "correo": "paola.vergara@hsi.mock",
                },
                {
                    "tipo_documento": "TI",
                    "numero_documento": "1020303311",
                    "nombres": "Santiago",
                    "apellidos": "Nuñez",
                    "fecha_nacimiento": date(2009, 2, 27),
                    "telefono": "3037003303",
                    "correo": "santiago.nunez@hsi.mock",
                },
            ],
            "especialidades": [
                "Medicina General",
                "Cardiología",
                "Ginecobstetricia",
                "Neurología",
                "Ortopedia",
                "Psicología",
            ],
            "prestadores": [
                {"nombre_completo": "Dra. Andrea Rocha", "especialidad": "Medicina General"},
                {"nombre_completo": "Dr. Nicolas Padilla", "especialidad": "Cardiología"},
                {"nombre_completo": "Dra. Laura Salcedo", "especialidad": "Ginecobstetricia"},
                {"nombre_completo": "Dra. Marcela Torres", "especialidad": "Neurología"},
                {"nombre_completo": "Dr. Luis Fontalvo", "especialidad": "Ortopedia"},
                {"nombre_completo": "Dr. Camilo Patiño", "especialidad": "Psicología"},
            ],
        },
        "IPS-MED": {
            "pacientes": [
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1014977178",
                    "nombres": "Adrian",
                    "apellidos": "Ruiz",
                    "fecha_nacimiento": date(2004, 8, 2),
                    "telefono": "573182273533",
                    "correo": "adrianrrruiz@gmail.com",
                },
                {
                    "tipo_documento": "CE",
                    "numero_documento": "485101",
                    "nombres": "Leo",
                    "apellidos": "Velazquez",
                    "fecha_nacimiento": date(2026, 4, 2),
                    "telefono": "+573208761377",
                    "correo": "levelazquez@javeriana.edu.co",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1099001001",
                    "nombres": "Samuel",
                    "apellidos": "Rios",
                    "fecha_nacimiento": date(1992, 9, 18),
                    "telefono": "3001110001",
                    "correo": "samuel.rios@med.mock",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1099001002",
                    "nombres": "Carolina",
                    "apellidos": "Vargas",
                    "fecha_nacimiento": date(1989, 2, 7),
                    "telefono": "3001110002",
                    "correo": "carolina.vargas@med.mock",
                },
            ],
            "especialidades": [
                "Medicina General",
                "Pediatría",
                "Dermatología",
                "Oftalmología",
                "Psicología",
                "Gastroenterología",
            ],
            "prestadores": [
                {"nombre_completo": "Dra. Luciana Suarez", "especialidad": "Medicina General"},
                {"nombre_completo": "Dr. Mateo Cardenas", "especialidad": "Pediatría"},
                {"nombre_completo": "Dr. Felipe Neira", "especialidad": "Dermatología"},
                {"nombre_completo": "Dra. Sandra Molina", "especialidad": "Oftalmología"},
                {"nombre_completo": "Dr. Camilo Patiño", "especialidad": "Psicología"},
                {"nombre_completo": "Dr. Julian Acosta", "especialidad": "Gastroenterología"},
            ],
        },
    }

    return by_ips.get(ips_code, defaults)
