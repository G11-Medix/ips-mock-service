from datetime import date, datetime, time, timedelta

from sqlmodel import Session, select

from app.config import get_settings
from app.models.entities import Appointment, IPS, Paciente, Provider, Specialty

SPECIALTY_REPS_CODES = {
    "medicina general": "101",
    "cardiologia": "302",
    "dermatologia": "312",
    "gastroenterologia": "315",
    "ginecobstetricia": "318",
    "neurologia": "329",
    "oftalmologia": "330",
    "ortopedia": "331",
    "pediatria": "335",
    "psicologia": "342",
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

    session.add(
        IPS(
            nombre=settings.ips_name,
            codigo=settings.ips_code,
            nit=settings.ips_nit,
            direccion="Direccion principal IPS mock",
            telefono="6017000000",
            estado="activo",
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
            "Medicina Familiar",
            "Pediatria",
            "Ginecobstetricia",
            "Odontologia General",
        ],
        "prestadores": [
            {"nombre_completo": "Dra. Luciana Suarez", "especialidad": "Medicina Familiar"},
            {"nombre_completo": "Dr. Mateo Cardenas", "especialidad": "Pediatria"},
            {"nombre_completo": "Dra. Diana Bernal", "especialidad": "Ginecobstetricia"},
            {"nombre_completo": "Dr. Julian Acosta", "especialidad": "Odontologia General"},
        ],
    }

    by_ips = {
        "IPS-CSH": {
            "pacientes": [
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1100101101",
                    "nombres": "Julian",
                    "apellidos": "Arenas",
                    "fecha_nacimiento": date(1991, 4, 11),
                    "telefono": "3015001101",
                    "correo": "julian.arenas@csh.mock",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1100101102",
                    "nombres": "Valentina",
                    "apellidos": "Pardo",
                    "fecha_nacimiento": date(1986, 10, 3),
                    "telefono": "3015001102",
                    "correo": "valentina.pardo@csh.mock",
                },
                {
                    "tipo_documento": "TI",
                    "numero_documento": "1002003011",
                    "nombres": "Camilo",
                    "apellidos": "Arias",
                    "fecha_nacimiento": date(2008, 5, 22),
                    "telefono": "3015001103",
                    "correo": "camilo.arias@csh.mock",
                },
            ],
            "especialidades": ["Medicina Interna", "Pediatria", "Odontologia", "Dermatologia"],
            "prestadores": [
                {"nombre_completo": "Dra. Paula Restrepo", "especialidad": "Medicina Interna"},
                {"nombre_completo": "Dr. Tomas Rojas", "especialidad": "Pediatria"},
                {"nombre_completo": "Dra. Sandra Molina", "especialidad": "Odontologia"},
                {"nombre_completo": "Dr. Felipe Neira", "especialidad": "Dermatologia"},
            ],
        },
        "IPS-HNH": {
            "pacientes": [
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1200202201",
                    "nombres": "Daniela",
                    "apellidos": "Mina",
                    "fecha_nacimiento": date(1993, 6, 14),
                    "telefono": "3026002201",
                    "correo": "daniela.mina@hnh.mock",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1200202202",
                    "nombres": "Ricardo",
                    "apellidos": "Sierra",
                    "fecha_nacimiento": date(1984, 12, 30),
                    "telefono": "3026002202",
                    "correo": "ricardo.sierra@hnh.mock",
                },
                {
                    "tipo_documento": "CE",
                    "numero_documento": "Y90022003",
                    "nombres": "Natalia",
                    "apellidos": "Duarte",
                    "fecha_nacimiento": date(1997, 8, 4),
                    "telefono": "3026002203",
                    "correo": "natalia.duarte@hnh.mock",
                },
            ],
            "especialidades": ["Medicina General", "Ginecologia", "Nutricion", "Psicologia"],
            "prestadores": [
                {"nombre_completo": "Dr. Hernan Quintero", "especialidad": "Medicina General"},
                {"nombre_completo": "Dra. Laura Salcedo", "especialidad": "Ginecologia"},
                {"nombre_completo": "Dra. Maria Isabel Ruiz", "especialidad": "Nutricion"},
                {"nombre_completo": "Dr. Camilo Patiño", "especialidad": "Psicologia"},
            ],
        },
        "IPS-CPC": {
            "pacientes": [
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1300303301",
                    "nombres": "Kevin",
                    "apellidos": "Barrios",
                    "fecha_nacimiento": date(1994, 1, 9),
                    "telefono": "3037003301",
                    "correo": "kevin.barrios@cpc.mock",
                },
                {
                    "tipo_documento": "CC",
                    "numero_documento": "1300303302",
                    "nombres": "Paola",
                    "apellidos": "Vergara",
                    "fecha_nacimiento": date(1987, 11, 19),
                    "telefono": "3037003302",
                    "correo": "paola.vergara@cpc.mock",
                },
                {
                    "tipo_documento": "TI",
                    "numero_documento": "1020303311",
                    "nombres": "Santiago",
                    "apellidos": "Nuñez",
                    "fecha_nacimiento": date(2009, 2, 27),
                    "telefono": "3037003303",
                    "correo": "santiago.nunez@cpc.mock",
                },
            ],
            "especialidades": ["Medicina Familiar", "Cardiologia", "Pediatria", "Fisiatria"],
            "prestadores": [
                {"nombre_completo": "Dra. Andrea Rocha", "especialidad": "Medicina Familiar"},
                {"nombre_completo": "Dr. Nicolas Padilla", "especialidad": "Cardiologia"},
                {"nombre_completo": "Dra. Johana Cotes", "especialidad": "Pediatria"},
                {"nombre_completo": "Dr. Luis Fontalvo", "especialidad": "Fisiatria"},
            ],
        },
    }

    return by_ips.get(ips_code, defaults)
