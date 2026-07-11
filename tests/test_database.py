from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import Database, validate_brazilian_phone
from app.system_service import prune_old_backups


def smoke_test() -> None:
    with TemporaryDirectory() as temp:
        temp_path = Path(temp)
        db = Database(str(temp_path / "test.db"))

        # Produtos iniciais.
        products = db.list_products(public_only=True)
        assert len(products) >= 1, (
            "O banco de testes deveria possuir pelo menos um produto inicial."
        )

        # Cadastro de produto com estoque.
        product_id = db.create_product(
            {
                "name": "Produto estoque",
                "description": "",
                "category": "Teste",
                "priceCents": 1000,
                "active": True,
                "available": True,
                "stockControlled": True,
                "stockQuantity": 10,
                "minimumStock": 3,
                "costCents": 500,
            }
        )

        created_product = next(
            product
            for product in db.list_products()
            if product["id"] == product_id
        )

        assert created_product["stock_controlled"] is True
        assert created_product["stock_quantity"] == 10
        assert created_product["minimum_stock"] == 3
        assert created_product["cost_cents"] == 500

        # Entrada de estoque.
        stock_result = db.adjust_stock(
            product_id,
            5,
            "ENTRY",
            "Teste",
        )
        assert stock_result["balance"] == 15

        movements = db.list_stock_movements(product_id=product_id)
        assert len(movements) >= 1
        assert movements[0]["movement_type"] == "ENTRY"
        assert movements[0]["balance_after"] == 15

        summary = db.stock_summary()
        assert summary["controlledProducts"] >= 1
        assert summary["totalUnits"] >= 15

        # Validação de telefone.
        assert (
            validate_brazilian_phone("(11)98765-4321")
            == "11987654321"
        )
        assert (
            validate_brazilian_phone("(11)3234-5678")
            == "1132345678"
        )

        try:
            validate_brazilian_phone("(00)98765-4321")
        except ValueError:
            pass
        else:
            raise AssertionError(
                "DDD inválido deveria ser rejeitado."
            )

        # Criação de pedido com produto inicial.
        order = db.create_order(
            {
                "customer": {
                    "name": "Cliente Teste",
                    "phone": "11999998888",
                },
                "items": [
                    {
                        "productId": 1,
                        "quantity": 2,
                    }
                ],
                "paymentMethod": "PIX",
            }
        )

        assert order is not None
        assert order["totalCents"] > 0
        assert order["status"] == "RECEIVED"

        # Consulta de clientes.
        customers = db.list_customers(query="Cliente")
        assert len(customers) >= 1
        assert customers[0]["orderCount"] >= 1

        # Histórico de status.
        assert order["statusTimeline"][0]["status"] == "RECEIVED"

        db.update_order_status(order["id"], "PREPARING")
        updated = db.get_order(order["id"])

        assert updated is not None
        assert [
            item["status"]
            for item in updated["statusTimeline"]
        ] == [
            "RECEIVED",
            "PREPARING",
        ]

        # Rastreamento.
        assert len(
            db.track_orders(phone="11999998888")
        ) == 1
        assert len(
            db.track_orders(code=order["code"])
        ) == 1
        assert len(
            db.track_orders(
                phone="11999998888",
                code=order["code"],
            )
        ) == 1

        # Retenção de backups.
        backup_dir = temp_path / "backups"
        backup_dir.mkdir()

        for index in range(5):
            file_path = (
                backup_dir
                / f"espetaria_20260711_12000{index}.db"
            )
            file_path.write_text(
                str(index),
                encoding="utf-8",
            )

        removed = prune_old_backups(
            str(backup_dir),
            keep=3,
        )

        assert len(removed) == 2
        assert len(
            list(backup_dir.glob("espetaria_*.db"))
        ) == 3


if __name__ == "__main__":
    smoke_test()
    print("Smoke test concluído.")
