from pathlib import Path
from tempfile import TemporaryDirectory

from app.database import Database


def smoke_test() -> None:
    with TemporaryDirectory() as temp:
        db = Database(str(Path(temp) / "test.db"))
        assert len(db.list_products(public_only=True)) >= 1
        order = db.create_order(
            {
                "customer": {"name": "Cliente Teste", "phone": "11999998888"},
                "items": [{"productId": 1, "quantity": 2}],
                "paymentMethod": "PIX",
            }
        )
        assert order["totalCents"] > 0
        assert db.track_order("11999998888", order["code"]) is not None


if __name__ == "__main__":
    smoke_test()
    print("Smoke test concluído.")
