from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tempfile import TemporaryDirectory

from app.database import Database, validate_brazilian_phone
from app.system_service import prune_old_backups


def smoke_test() -> None:
    with TemporaryDirectory() as temp:
        db = Database(str(Path(temp) / "test.db"))
        assert len(db.list_products(public_only=True)) >= 1
        assert validate_brazilian_phone("(11)98765-4321") == "11987654321"
        assert validate_brazilian_phone("(11)3234-5678") == "1132345678"
        try:
            validate_brazilian_phone("(00)98765-4321")
            raise AssertionError("DDD inválido deveria ser rejeitado")
        except ValueError:
            pass
        order = db.create_order(
            {
                "customer": {"name": "Cliente Teste", "phone": "11999998888"},
                "items": [{"productId": 1, "quantity": 2}],
                "paymentMethod": "PIX",
            }
        )
        assert order["totalCents"] > 0
        customers = db.list_customers(query="Cliente")
        assert len(customers) >= 1
        assert customers[0]["orderCount"] >= 1

        backup_dir = Path(temp_dir) / "backups"
        backup_dir.mkdir()
        for index in range(5):
            file = backup_dir / f"espetaria_20260711_12000{index}.db"
            file.write_text(str(index), encoding="utf-8")
        removed = prune_old_backups(str(backup_dir), keep=3)
        assert len(removed) == 2
        assert len(list(backup_dir.glob("espetaria_*.db"))) == 3
        assert order["statusTimeline"][0]["status"] == "RECEIVED"
        db.update_order_status(order["id"], "PREPARING")
        updated = db.get_order(order["id"])
        assert updated is not None
        assert [item["status"] for item in updated["statusTimeline"]] == ["RECEIVED", "PREPARING"]
        assert len(db.track_orders(phone="11999998888")) == 1
        assert len(db.track_orders(code=order["code"])) == 1
        assert len(
            db.track_orders(phone="11999998888", code=order["code"])
        ) == 1


if __name__ == "__main__":
    smoke_test()
    print("Smoke test concluído.")
