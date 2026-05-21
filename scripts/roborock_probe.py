import argparse
import asyncio
import getpass
import json
import os
import pickle
from pathlib import Path
from typing import Any


CACHE_DIR = Path.home() / ".fibaro10"
CACHE_FILE = CACHE_DIR / "roborock_user_data.pickle"


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return jsonable(value.model_dump())
    if hasattr(value, "dict"):
        return jsonable(value.dict())
    if hasattr(value, "__dict__"):
        return jsonable({key: item for key, item in vars(value).items() if not key.startswith("_")})
    return str(value)


def print_json(value: Any) -> None:
    print(json.dumps(jsonable(value), indent=2, ensure_ascii=False, default=str))


def save_user_data(user_data: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with CACHE_FILE.open("wb") as file:
        pickle.dump(user_data, file)


def load_user_data() -> Any:
    if not CACHE_FILE.exists():
        raise SystemExit(
            "Mangler lagret Roborock-login. Kjør først:\n"
            "  python scripts/roborock_probe.py request-code --email DIN_EPOST\n"
            "  python scripts/roborock_probe.py login --email DIN_EPOST --code KODE"
        )
    with CACHE_FILE.open("rb") as file:
        return pickle.load(file)


async def request_code(email: str) -> None:
    from roborock.web_api import RoborockApiClient

    web_api = RoborockApiClient(username=email)
    await web_api.request_code()
    print(f"Kode er sendt til {email}.")


async def login(email: str, code: str) -> None:
    from roborock.web_api import RoborockApiClient

    web_api = RoborockApiClient(username=email)
    user_data = await web_api.code_login(code)
    save_user_data(user_data)
    print(f"Login lagret i {CACHE_FILE}")
    print_json(user_data)


async def password_login(email: str, password: str | None, password_env: str | None) -> None:
    from roborock.web_api import RoborockApiClient

    if password_env:
        password = os.getenv(password_env)
    if not password:
        password = getpass.getpass("Roborock-passord: ")
    if not password:
        raise SystemExit("Mangler passord.")

    web_api = RoborockApiClient(username=email)
    user_data = await web_api.pass_login(password)
    save_user_data(user_data)
    print(f"Login lagret i {CACHE_FILE}")
    print_json(user_data)


async def get_device_manager(email: str):
    from roborock.devices.device_manager import UserParams, create_device_manager

    user_data = load_user_data()
    user_params = UserParams(username=email, user_data=user_data)
    return await create_device_manager(user_params)


async def list_devices(email: str) -> None:
    manager = await get_device_manager(email)
    devices = await manager.get_devices()
    result = []
    for device in devices:
        result.append(
            {
                "name": getattr(device, "name", None),
                "duid": getattr(device, "duid", None),
                "model": getattr(device, "model", None),
                "category": getattr(device, "category", None),
                "has_v1_properties": bool(getattr(device, "v1_properties", None)),
                "has_a01_properties": bool(getattr(device, "a01_properties", None)),
            }
        )
    print_json(result)


async def show_status(email: str) -> None:
    manager = await get_device_manager(email)
    devices = await manager.get_devices()
    result = []
    for device in devices:
        item = {
            "name": getattr(device, "name", None),
            "duid": getattr(device, "duid", None),
            "model": getattr(device, "model", None),
        }
        properties = getattr(device, "v1_properties", None)
        if properties and getattr(properties, "status", None):
            await properties.status.refresh()
            item["status"] = jsonable(properties.status)
        if properties and getattr(properties, "consumables", None):
            await properties.consumables.refresh()
            item["consumables"] = jsonable(properties.consumables)
        result.append(item)
    print_json(result)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Roborock API-test for Fibaro10/SUN2.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    request_parser = subparsers.add_parser("request-code", help="Send Roborock innloggingskode på e-post.")
    request_parser.add_argument("--email", required=True)

    login_parser = subparsers.add_parser("login", help="Logg inn med kode og lagre brukerdata lokalt.")
    login_parser.add_argument("--email", required=True)
    login_parser.add_argument("--code", required=True)

    password_parser = subparsers.add_parser("password-login", help="Logg inn med passord og lagre brukerdata lokalt.")
    password_parser.add_argument("--email", required=True)
    password_parser.add_argument("--password", help="Unngå helst denne. Bruk prompt eller --password-env.")
    password_parser.add_argument("--password-env", help="Navn på miljøvariabel som inneholder passordet.")

    devices_parser = subparsers.add_parser("devices", help="List Roborock-enheter på kontoen.")
    devices_parser.add_argument("--email", required=True)

    status_parser = subparsers.add_parser("status", help="Hent status og forbruksdeler for støvsugere.")
    status_parser.add_argument("--email", required=True)

    args = parser.parse_args()

    if args.command == "request-code":
        await request_code(args.email)
    elif args.command == "login":
        await login(args.email, args.code)
    elif args.command == "password-login":
        await password_login(args.email, args.password, args.password_env)
    elif args.command == "devices":
        await list_devices(args.email)
    elif args.command == "status":
        await show_status(args.email)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ModuleNotFoundError as exc:
        if exc.name == "roborock":
            raise SystemExit(
                "Python-pakken mangler. Installer først:\n"
                "  python -m pip install python-roborock"
            ) from exc
        raise
