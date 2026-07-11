from __future__ import annotations

import random
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.security import hash_password, new_salt


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


VALID_BRAZILIAN_DDDS = {
    "11", "12", "13", "14", "15", "16", "17", "18", "19",
    "21", "22", "24", "27", "28",
    "31", "32", "33", "34", "35", "37", "38",
    "41", "42", "43", "44", "45", "46", "47", "48", "49",
    "51", "53", "54", "55",
    "61", "62", "63", "64", "65", "66", "67", "68", "69",
    "71", "73", "74", "75", "77", "79",
    "81", "82", "83", "84", "85", "86", "87", "88", "89",
    "91", "92", "93", "94", "95", "96", "97", "98", "99",
}


def validate_brazilian_phone(value: str) -> str:
    phone = normalize_phone(value)

    if len(phone) not in {10, 11}:
        raise ValueError("Informe um telefone válido com DDD.")

    if phone[:2] not in VALID_BRAZILIAN_DDDS:
        raise ValueError("Informe um DDD brasileiro válido.")

    if len(set(phone[2:])) == 1:
        raise ValueError("Informe um número de telefone válido.")

    return phone


def make_order_code() -> str:
    now = datetime.now()
    return f"ESP-{now:%Y%m%d}-{random.SystemRandom().randint(1000, 9999)}"


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.migrate()
        self.ensure_extensions()
        self.seed()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def migrate(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('ADMIN','ATTENDANT')),
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL UNIQUE,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'Espetos',
                    price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
                    active INTEGER NOT NULL DEFAULT 1,
                    available INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    customer_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    payment_method TEXT NOT NULL DEFAULT 'PIX',
                    payment_status TEXT NOT NULL DEFAULT 'PENDING',
                    total_cents INTEGER NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(customer_id) REFERENCES customers(id)
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
                    unit_price_cents INTEGER NOT NULL,
                    subtotal_cents INTEGER NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY(product_id) REFERENCES products(id)
                );
                CREATE TABLE IF NOT EXISTS order_status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    entered_at TEXT NOT NULL,
                    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_order_status_history_order
                    ON order_status_history(order_id, entered_at);

                CREATE TABLE IF NOT EXISTS cash_registers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opened_by INTEGER NOT NULL,
                    opened_at TEXT NOT NULL,
                    opening_cents INTEGER NOT NULL,
                    closed_by INTEGER,
                    closed_at TEXT,
                    closing_cents INTEGER,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    FOREIGN KEY(opened_by) REFERENCES users(id),
                    FOREIGN KEY(closed_by) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS cash_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cash_register_id INTEGER NOT NULL,
                    order_id INTEGER,
                    type TEXT NOT NULL,
                    payment_method TEXT NOT NULL,
                    value_cents INTEGER NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(cash_register_id) REFERENCES cash_registers(id),
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                );
                """
            )

    def ensure_extensions(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    user_name TEXT NOT NULL DEFAULT '',
                    action TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at
                    ON audit_logs(created_at);
                """
            )

            orders = conn.execute(
                """
                SELECT id, status, created_at, updated_at
                FROM orders
                WHERE NOT EXISTS (
                    SELECT 1 FROM order_status_history h
                    WHERE h.order_id = orders.id
                )
                """
            ).fetchall()

            for order in orders:
                conn.execute(
                    """
                    INSERT INTO order_status_history(order_id, status, entered_at)
                    VALUES (?, 'RECEIVED', ?)
                    """,
                    (order["id"], order["created_at"]),
                )
                if order["status"] != "RECEIVED":
                    conn.execute(
                        """
                        INSERT INTO order_status_history(order_id, status, entered_at)
                        VALUES (?, ?, ?)
                        """,
                        (order["id"], order["status"], order["updated_at"]),
                    )

    def add_audit_log(
        self,
        action: str,
        details: str = "",
        user_id: int | None = None,
        user_name: str = "",
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs(user_id, user_name, action, details, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, user_name, action, details, utc_now()),
            )

    def recent_audit_logs(
        self,
        limit: int = 100,
        action: str = "",
        user_name: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        conditions: list[str] = []
        values: list[Any] = []
        if action.strip():
            conditions.append("action = ?")
            values.append(action.strip().upper())
        if user_name.strip():
            conditions.append("LOWER(user_name) LIKE LOWER(?)")
            values.append(f"%{user_name.strip()}%")
        if start_date.strip():
            conditions.append("date(created_at) >= date(?)")
            values.append(start_date.strip())
        if end_date.strip():
            conditions.append("date(created_at) <= date(?)")
            values.append(end_date.strip())
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        values.append(limit)
        with self.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT id, user_id, user_name, action, details, created_at
                FROM audit_logs
                {where}
                ORDER BY id DESC
                LIMIT ?
                """,
                values,
            ).fetchall()
        return [dict(row) for row in rows]

    def list_customers(self, query: str = "", limit: int = 300) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 1000))
        values: list[Any] = []
        where = ""
        if query.strip():
            normalized = normalize_phone(query)
            where = "WHERE LOWER(c.name) LIKE LOWER(?) OR c.phone LIKE ?"
            values.extend([f"%{query.strip()}%", f"%{normalized}%"])
        values.append(safe_limit)
        with self.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT c.id, c.name, c.phone, c.created_at,
                       COUNT(o.id) AS order_count,
                       COALESCE(SUM(CASE WHEN o.payment_status='PAID'
                           THEN o.total_cents ELSE 0 END), 0) AS paid_total_cents,
                       MAX(o.created_at) AS last_order_at
                FROM customers c
                LEFT JOIN orders o ON o.customer_id = c.id
                {where}
                GROUP BY c.id, c.name, c.phone, c.created_at
                ORDER BY CASE WHEN MAX(o.created_at) IS NULL THEN 1 ELSE 0 END,
                         MAX(o.created_at) DESC, c.name
                LIMIT ?
                """,
                values,
            ).fetchall()
        return [{
            "id": row["id"], "name": row["name"], "phone": row["phone"],
            "createdAt": row["created_at"],
            "orderCount": int(row["order_count"] or 0),
            "paidTotalCents": int(row["paid_total_cents"] or 0),
            "lastOrderAt": row["last_order_at"],
        } for row in rows]

    def statistics(self) -> dict[str, Any]:
        with self.connection() as conn:
            customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
            products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            available = conn.execute(
                "SELECT COUNT(*) FROM products WHERE active=1 AND available=1"
            ).fetchone()[0]
            orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            active_orders = conn.execute(
                """
                SELECT COUNT(*) FROM orders
                WHERE status NOT IN ('DELIVERED','CANCELLED')
                """
            ).fetchone()[0]
            paid_total = conn.execute(
                """
                SELECT COALESCE(SUM(total_cents),0) FROM orders
                WHERE payment_status='PAID'
                """
            ).fetchone()[0]
        return {
            "customers": customers,
            "products": products,
            "availableProducts": available,
            "orders": orders,
            "activeOrders": active_orders,
            "paidTotalCents": paid_total,
        }

    def seed(self) -> None:
        with self.connection() as conn:
            if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                self._insert_user(conn, "Administrador", "admin", "admin123", "ADMIN")
                self._insert_user(
                    conn, "Atendente", "atendente", "atendente123", "ATTENDANT"
                )

            if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
                now = utc_now()
                products = [
                    ("Espeto de carne", "Carne bovina temperada.", "Espetos", 1200),
                    ("Espeto de frango", "Frango temperado.", "Espetos", 1000),
                    ("Espeto de linguiça", "Linguiça toscana.", "Espetos", 1000),
                    ("Pão de alho", "Pão de alho cremoso.", "Acompanhamentos", 800),
                    ("Refrigerante lata", "Lata 350 ml.", "Bebidas", 600),
                    ("Água mineral", "Garrafa 500 ml.", "Bebidas", 400),
                ]
                conn.executemany(
                    """
                    INSERT INTO products
                    (name, description, category, price_cents, active, available,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, 1, 1, ?, ?)
                    """,
                    [(n, d, c, p, now, now) for n, d, c, p in products],
                )

    def _insert_user(
        self,
        conn: sqlite3.Connection,
        name: str,
        username: str,
        password: str,
        role: str,
    ) -> None:
        salt = new_salt()
        conn.execute(
            """
            INSERT INTO users
            (name, username, password_hash, salt, role, active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (name, username, hash_password(password, salt), salt, role, utc_now()),
        )

    @staticmethod
    def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    def list_products(self, public_only: bool = False) -> list[dict[str, Any]]:
        where = "WHERE active = 1 AND available = 1" if public_only else ""
        with self.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT id, name, description, category, price_cents,
                       active, available, created_at, updated_at
                FROM products {where}
                ORDER BY category, name
                """
            ).fetchall()
        return [
            {
                **dict(row),
                "active": bool(row["active"]),
                "available": bool(row["available"]),
            }
            for row in rows
        ]

    def authenticate(self, username: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT id, name, username, password_hash, salt, role
                FROM users WHERE username = ? AND active = 1
                """,
                (username.strip(),),
            ).fetchone()
        return self._dict(row)

    def upsert_customer(self, name: str, phone: str) -> dict[str, Any]:
        name = name.strip()
        phone = validate_brazilian_phone(phone)
        if len(name) < 2:
            raise ValueError("Informe um nome válido.")

        now = utc_now()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO customers(name, phone, active, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(phone) DO UPDATE SET
                    name = excluded.name,
                    active = 1,
                    updated_at = excluded.updated_at
                """,
                (name, phone, now, now),
            )
            row = conn.execute(
                "SELECT id, name, phone FROM customers WHERE phone = ?",
                (phone,),
            ).fetchone()
        return dict(row)

    def create_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        customer_data = payload.get("customer") or {}
        items = payload.get("items") or []
        if not isinstance(items, list) or not items:
            raise ValueError("Adicione ao menos um produto.")

        customer = self.upsert_customer(
            str(customer_data.get("name", "")),
            str(customer_data.get("phone", "")),
        )

        validated: list[dict[str, Any]] = []
        total = 0
        with self.connection() as conn:
            for raw in items:
                product_id = int(raw.get("productId", 0))
                quantity = int(raw.get("quantity", 0))
                if product_id <= 0 or not 1 <= quantity <= 50:
                    raise ValueError("Item do pedido inválido.")

                product = conn.execute(
                    """
                    SELECT id, name, price_cents FROM products
                    WHERE id = ? AND active = 1 AND available = 1
                    """,
                    (product_id,),
                ).fetchone()
                if product is None:
                    raise ValueError(f"Produto {product_id} indisponível.")

                subtotal = product["price_cents"] * quantity
                total += subtotal
                validated.append(
                    {
                        "productId": product["id"],
                        "name": product["name"],
                        "quantity": quantity,
                        "unitPriceCents": product["price_cents"],
                        "subtotalCents": subtotal,
                        "notes": str(raw.get("notes", "")),
                    }
                )

            code = make_order_code()
            now = utc_now()
            cursor = conn.execute(
                """
                INSERT INTO orders
                (code, customer_id, status, payment_method, payment_status,
                 total_cents, notes, created_at, updated_at)
                VALUES (?, ?, 'RECEIVED', ?, 'PENDING', ?, ?, ?, ?)
                """,
                (
                    code,
                    customer["id"],
                    str(payload.get("paymentMethod", "PIX")).upper(),
                    total,
                    str(payload.get("notes", "")),
                    now,
                    now,
                ),
            )
            order_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO order_status_history(order_id, status, entered_at)
                VALUES (?, 'RECEIVED', ?)
                """,
                (order_id, now),
            )
            conn.executemany(
                """
                INSERT INTO order_items
                (order_id, product_id, product_name, quantity,
                 unit_price_cents, subtotal_cents, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        order_id,
                        item["productId"],
                        item["name"],
                        item["quantity"],
                        item["unitPriceCents"],
                        item["subtotalCents"],
                        item["notes"],
                    )
                    for item in validated
                ],
            )

        return self.get_order(int(order_id))  # type: ignore[arg-type]

    def order_status_timeline(self, order_id: int) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT status, entered_at
                FROM order_status_history
                WHERE order_id = ?
                ORDER BY entered_at, id
                """,
                (order_id,),
            ).fetchall()

        timeline: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            entered_at = datetime.fromisoformat(row["entered_at"])
            left_at = (
                datetime.fromisoformat(rows[index + 1]["entered_at"])
                if index + 1 < len(rows)
                else datetime.now(timezone.utc)
            )
            timeline.append({
                "status": row["status"],
                "enteredAt": row["entered_at"],
                "leftAt": rows[index + 1]["entered_at"] if index + 1 < len(rows) else None,
                "durationSeconds": max(0, int((left_at - entered_at).total_seconds())),
                "current": index == len(rows) - 1,
            })
        return timeline

    def get_order(self, order_id: int) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT o.*, c.name AS customer_name, c.phone AS customer_phone
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE o.id = ?
                """,
                (order_id,),
            ).fetchone()
            if row is None:
                return None
            items = conn.execute(
                """
                SELECT product_id, product_name, quantity, unit_price_cents,
                       subtotal_cents, notes
                FROM order_items WHERE order_id = ? ORDER BY id
                """,
                (order_id,),
            ).fetchall()

        return {
            "id": row["id"],
            "code": row["code"],
            "status": row["status"],
            "paymentMethod": row["payment_method"],
            "paymentStatus": row["payment_status"],
            "totalCents": row["total_cents"],
            "notes": row["notes"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "customer": {
                "id": row["customer_id"],
                "name": row["customer_name"],
                "phone": row["customer_phone"],
            },
            "items": [
                {
                    "productId": item["product_id"],
                    "name": item["product_name"],
                    "quantity": item["quantity"],
                    "unitPriceCents": item["unit_price_cents"],
                    "subtotalCents": item["subtotal_cents"],
                    "notes": item["notes"],
                }
                for item in items
            ],
            "statusTimeline": self.order_status_timeline(order_id),
        }

    def track_orders(
        self,
        phone: str = "",
        code: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        normalized_phone = normalize_phone(phone)
        normalized_code = code.strip()

        if not normalized_phone and not normalized_code:
            raise ValueError("Informe o telefone ou o código do pedido.")

        conditions: list[str] = []
        values: list[Any] = []

        if normalized_phone:
            normalized_phone = validate_brazilian_phone(normalized_phone)
            conditions.append("c.phone = ?")
            values.append(normalized_phone)

        if normalized_code:
            conditions.append("UPPER(o.code) = UPPER(?)")
            values.append(normalized_code)

        safe_limit = max(1, min(int(limit), 50))
        values.append(safe_limit)

        with self.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT o.id
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE {' AND '.join(conditions)}
                ORDER BY o.created_at DESC
                LIMIT ?
                """,
                values,
            ).fetchall()

        return [
            order
            for row in rows
            if (order := self.get_order(int(row["id"]))) is not None
        ]

    def list_orders(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id FROM orders
                ORDER BY CASE status
                    WHEN 'RECEIVED' THEN 1
                    WHEN 'PREPARING' THEN 2
                    WHEN 'READY' THEN 3
                    WHEN 'DELIVERED' THEN 4
                    ELSE 5 END,
                    created_at DESC
                LIMIT 200
                """
            ).fetchall()
        return [order for row in rows if (order := self.get_order(row["id"]))]

    def update_order_status(self, order_id: int, status: str) -> None:
        allowed = {"RECEIVED", "PREPARING", "READY", "DELIVERED", "CANCELLED"}
        if status not in allowed:
            raise ValueError("Status inválido.")
        now = utc_now()
        with self.connection() as conn:
            current = conn.execute(
                "SELECT status FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()
            if current is None:
                raise ValueError("Pedido não encontrado.")
            if current["status"] == status:
                return
            conn.execute(
                "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, order_id),
            )
            conn.execute(
                """
                INSERT INTO order_status_history(order_id, status, entered_at)
                VALUES (?, ?, ?)
                """,
                (order_id, status, now),
            )

    def create_product(self, data: dict[str, Any]) -> int:
        name = str(data.get("name", "")).strip()
        price = int(data.get("priceCents", -1))
        if len(name) < 2 or price < 0:
            raise ValueError("Nome e preço são obrigatórios.")
        now = utc_now()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO products
                (name, description, category, price_cents, active, available,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    str(data.get("description", "")),
                    str(data.get("category", "Espetos")).strip() or "Espetos",
                    price,
                    int(bool(data.get("active", True))),
                    int(bool(data.get("available", True))),
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def update_product(self, product_id: int, data: dict[str, Any]) -> None:
        name = str(data.get("name", "")).strip()
        price = int(data.get("priceCents", -1))
        if len(name) < 2 or price < 0:
            raise ValueError("Nome e preço são obrigatórios.")
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE products SET name=?, description=?, category=?,
                    price_cents=?, active=?, available=?, updated_at=?
                WHERE id=?
                """,
                (
                    name,
                    str(data.get("description", "")),
                    str(data.get("category", "Espetos")).strip() or "Espetos",
                    price,
                    int(bool(data.get("active", True))),
                    int(bool(data.get("available", True))),
                    utc_now(),
                    product_id,
                ),
            )

    def delete_product(self, product_id: int) -> None:
        with self.connection() as conn:
            used = conn.execute(
                "SELECT COUNT(*) FROM order_items WHERE product_id = ?",
                (product_id,),
            ).fetchone()[0]
            if used:
                conn.execute(
                    """
                    UPDATE products SET active=0, available=0, updated_at=?
                    WHERE id=?
                    """,
                    (utc_now(), product_id),
                )
            else:
                conn.execute("DELETE FROM products WHERE id=?", (product_id,))

    def list_sales(self, code: str = "", customer: str = "", phone: str = "", status: str = "", payment_method: str = "", payment_status: str = "", start_date: str = "", end_date: str = "", limit: int = 300) -> list[dict[str, Any]]:
        conditions=[]; values=[]
        if code.strip(): conditions.append("UPPER(o.code) LIKE UPPER(?)"); values.append(f"%{code.strip()}%")
        if customer.strip(): conditions.append("LOWER(c.name) LIKE LOWER(?)"); values.append(f"%{customer.strip()}%")
        if normalize_phone(phone): conditions.append("c.phone LIKE ?"); values.append(f"%{normalize_phone(phone)}%")
        if status.strip(): conditions.append("o.status=?"); values.append(status.strip().upper())
        if payment_method.strip(): conditions.append("o.payment_method=?"); values.append(payment_method.strip().upper())
        if payment_status.strip(): conditions.append("o.payment_status=?"); values.append(payment_status.strip().upper())
        if start_date.strip(): conditions.append("date(o.created_at)>=date(?)"); values.append(start_date.strip())
        if end_date.strip(): conditions.append("date(o.created_at)<=date(?)"); values.append(end_date.strip())
        where=f"WHERE {' AND '.join(conditions)}" if conditions else ""
        values.append(max(1,min(limit,1000)))
        with self.connection() as conn:
            rows=conn.execute(f"SELECT o.id FROM orders o JOIN customers c ON c.id=o.customer_id {where} ORDER BY o.created_at DESC LIMIT ?",values).fetchall()
        return [o for r in rows if (o:=self.get_order(r["id"]))]

    def dashboard_metrics(self) -> dict[str, Any]:
        with self.connection() as conn:
            row=conn.execute("SELECT COUNT(*) orders, COALESCE(SUM(CASE WHEN payment_status='PAID' THEN total_cents ELSE 0 END),0) revenue FROM orders WHERE date(created_at)=date('now','localtime')").fetchone()
            paid=conn.execute("SELECT COUNT(*) FROM orders WHERE date(created_at)=date('now','localtime') AND payment_status='PAID'").fetchone()[0]
            cancelled=conn.execute("SELECT COUNT(*) FROM orders WHERE date(created_at)=date('now','localtime') AND status='CANCELLED'").fetchone()[0]
        revenue=int(row['revenue'] or 0)
        return {"ordersToday":int(row['orders'] or 0),"revenueTodayCents":revenue,"averageTicketCents":int(revenue/paid) if paid else 0,"cancelledToday":int(cancelled)}

    def cash_history(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows=conn.execute("SELECT cr.*,uo.name opened_by_name,uc.name closed_by_name FROM cash_registers cr JOIN users uo ON uo.id=cr.opened_by LEFT JOIN users uc ON uc.id=cr.closed_by ORDER BY cr.id DESC LIMIT ?",(max(1,min(limit,500)),)).fetchall()
            result=[]
            for row in rows:
                t=conn.execute("SELECT COALESCE(SUM(CASE WHEN type='SALE' THEN value_cents ELSE 0 END),0) sales,COALESCE(SUM(CASE WHEN type='SUPPLY' THEN value_cents ELSE 0 END),0) supplies,COALESCE(SUM(CASE WHEN type='WITHDRAWAL' THEN value_cents ELSE 0 END),0) withdrawals FROM cash_movements WHERE cash_register_id=?",(row['id'],)).fetchone()
                expected=int(row['opening_cents'])+int(t['sales'])+int(t['supplies'])-int(t['withdrawals']); closing=row['closing_cents']
                result.append({"id":row['id'],"openedAt":row['opened_at'],"closedAt":row['closed_at'],"openedBy":row['opened_by_name'],"closedBy":row['closed_by_name'],"openingCents":row['opening_cents'],"closingCents":closing,"status":row['status'],"salesCents":t['sales'],"suppliesCents":t['supplies'],"withdrawalsCents":t['withdrawals'],"expectedCents":expected,"differenceCents":int(closing)-expected if closing is not None else None})
        return result

    def add_cash_movement(self, movement_type: str, value_cents: int, description: str, payment_method: str = "CASH") -> int:
        movement_type=movement_type.upper()
        if movement_type not in {"SUPPLY","WITHDRAWAL"}: raise ValueError("Tipo de movimentação inválido.")
        if value_cents<=0: raise ValueError("Informe um valor maior que zero.")
        current=self.current_cash()
        if current is None: raise ValueError("Não existe caixa aberto.")
        with self.connection() as conn:
            cur=conn.execute("INSERT INTO cash_movements(cash_register_id,order_id,type,payment_method,value_cents,description,created_at) VALUES (?,NULL,?,?,?,?,?)",(current['id'],movement_type,payment_method.upper(),value_cents,description.strip(),utc_now()))
            return int(cur.lastrowid)

    def current_cash(self) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT cr.*, u.name AS opened_by_name
                FROM cash_registers cr
                JOIN users u ON u.id = cr.opened_by
                WHERE cr.status='OPEN' ORDER BY cr.id DESC LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            totals = conn.execute(
                """
                SELECT payment_method, COALESCE(SUM(value_cents),0) AS total
                FROM cash_movements
                WHERE cash_register_id=? AND type='SALE'
                GROUP BY payment_method
                """,
                (row["id"],),
            ).fetchall()
        return {
            "id": row["id"],
            "openedAt": row["opened_at"],
            "openingCents": row["opening_cents"],
            "openedBy": row["opened_by_name"],
            "status": row["status"],
            "totals": {item["payment_method"]: item["total"] for item in totals},
        }

    def open_cash(self, user_id: int, opening_cents: int) -> None:
        if self.current_cash() is not None:
            raise ValueError("Já existe um caixa aberto.")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO cash_registers
                (opened_by, opened_at, opening_cents, status)
                VALUES (?, ?, ?, 'OPEN')
                """,
                (user_id, utc_now(), opening_cents),
            )

    def close_cash(self, user_id: int, closing_cents: int) -> None:
        current = self.current_cash()
        if current is None:
            raise ValueError("Não existe caixa aberto.")
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE cash_registers SET closed_by=?, closed_at=?,
                    closing_cents=?, status='CLOSED' WHERE id=?
                """,
                (user_id, utc_now(), closing_cents, current["id"]),
            )

    def register_payment(self, order_id: int, method: str) -> None:
        method = method.upper()
        if method not in {"PIX", "CASH", "CARD"}:
            raise ValueError("Forma de pagamento inválida.")
        current = self.current_cash()
        if current is None:
            raise ValueError("Abra o caixa antes de confirmar pagamentos.")
        order = self.get_order(order_id)
        if order is None:
            raise ValueError("Pedido não encontrado.")

        with self.connection() as conn:
            exists = conn.execute(
                """
                SELECT COUNT(*) FROM cash_movements
                WHERE order_id=? AND type='SALE'
                """,
                (order_id,),
            ).fetchone()[0]
            if not exists:
                conn.execute(
                    """
                    INSERT INTO cash_movements
                    (cash_register_id, order_id, type, payment_method,
                     value_cents, description, created_at)
                    VALUES (?, ?, 'SALE', ?, ?, ?, ?)
                    """,
                    (
                        current["id"],
                        order_id,
                        method,
                        order["totalCents"],
                        f"Pagamento do pedido {order['code']}",
                        utc_now(),
                    ),
                )
            conn.execute(
                """
                UPDATE orders SET payment_status='PAID', payment_method=?,
                    updated_at=? WHERE id=?
                """,
                (method, utc_now(), order_id),
            )
