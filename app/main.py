from __future__ import annotations

import sys
from pathlib import Path

# Permite executar este arquivo diretamente pelo VS Code:
# python app/main.py
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import asyncio
import time
from typing import Any
import csv
import io

from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.database import Database
from app.security import new_token, verify_password
from app.realtime import realtime
from app.system_service import (
    create_backup,
    create_daily_backup_if_needed,
    database_integrity,
    prune_old_backups,
    list_backups,
    safe_backup_path,
    system_info,
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="EspetariaOS API",
    version="1.0.1",
    description="MVP para catálogo, pedidos, caixa e administração.",
    docs_url="/docs" if settings.development else None,
    redoc_url="/redoc" if settings.development else None,
    openapi_url="/openapi.json" if settings.development else None,
)
database = Database(settings.database_path)


@dataclass
class Session:
    user_id: int
    name: str
    role: str
    expires_at: datetime


sessions: dict[str, Session] = {}
login_attempts: dict[str, list[float]] = {}
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_ATTEMPTS = 5


class LoginInput(BaseModel):
    username: str
    password: str


class CustomerInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=20)


class OrderItemInput(BaseModel):
    productId: int
    quantity: int = Field(ge=1, le=50)
    notes: str = Field(default="", max_length=300)


class OrderInput(BaseModel):
    customer: CustomerInput
    items: list[OrderItemInput]
    paymentMethod: str = "PIX"
    notes: str = Field(default="", max_length=500)


class StatusInput(BaseModel):
    status: str
    confirmUnpaidDelivery: bool = False


class PaymentInput(BaseModel):
    method: str


class CashInput(BaseModel):
    valueCents: int = Field(ge=0)


class CashMovementInput(BaseModel):
    valueCents: int = Field(gt=0)
    description: str = Field(default="", max_length=300)


class ExpenseInput(BaseModel):
    description: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=80)
    paymentMethod: str
    valueCents: int = Field(gt=0)
    expenseDate: str
    notes: str = Field(default="", max_length=500)


class ProductInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    category: str = Field(default="Espetos", max_length=80)
    priceCents: int = Field(ge=0)
    active: bool = True
    available: bool = True
    stockControlled: bool = False
    stockQuantity: int = Field(default=0, ge=0)
    minimumStock: int = Field(default=0, ge=0)
    costCents: int = Field(default=0, ge=0)


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Não autenticado.")
    return authorization[7:]


def current_session(token: str = Depends(bearer_token)) -> Session:
    session = sessions.get(token)
    if session is None or session.expires_at < datetime.now(timezone.utc):
        sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    return session


def admin_session(session: Session = Depends(current_session)) -> Session:
    if session.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador.")
    return session


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


async def run_automatic_backup_cycle() -> None:
    if not settings.automatic_backup:
        return
    try:
        backup = create_daily_backup_if_needed(settings.database_path, settings.backups_dir)
        if backup is not None:
            database.add_audit_log("AUTOMATIC_BACKUP_CREATED", backup.name, user_name="Sistema")
        removed = prune_old_backups(settings.backups_dir, settings.backup_retention)
        if removed:
            database.add_audit_log(
                "OLD_BACKUPS_REMOVED",
                f"{len(removed)} backup(s) removido(s): {', '.join(removed)}",
                user_name="Sistema",
            )
    except Exception as exc:
        database.add_audit_log("AUTOMATIC_BACKUP_FAILED", str(exc), user_name="Sistema")

async def automatic_backup_loop() -> None:
    while True:
        await run_automatic_backup_cycle()
        await asyncio.sleep(max(5, settings.backup_check_minutes) * 60)

@app.on_event("startup")
async def start_background_tasks() -> None:
    await run_automatic_backup_cycle()
    asyncio.create_task(automatic_backup_loop())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await realtime.connect(websocket)
    try:
        await websocket.send_json({
            "event": "CONNECTED",
            "payload": {"service": "EspetariaOS", "version": "1.0.1"},
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime.disconnect(websocket)
    except Exception:
        realtime.disconnect(websocket)


@app.get("/api/health")
def health() -> dict[str, Any]:
    integrity = database_integrity(settings.database_path)
    return {
        "ok": integrity["ok"],
        "service": "EspetariaOS",
        "version": "1.0.1",
        "environment": settings.environment,
        "database": integrity,
        "automaticBackup": settings.automatic_backup,
    }


@app.get("/api/products")
def products() -> dict[str, Any]:
    return {"items": database.list_products(public_only=True)}


@app.post("/api/customers", status_code=201)
def create_customer(data: CustomerInput) -> dict[str, Any]:
    try:
        return database.upsert_customer(data.name, data.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/orders", status_code=201)
async def create_order(data: OrderInput) -> dict[str, Any]:
    try:
        order = database.create_order(data.model_dump())
        database.add_audit_log(
            "ORDER_CREATED",
            f"Pedido {order['code']} criado por {order['customer']['name']}",
        )
        await realtime.broadcast("ORDER_CREATED", order)
        return order
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/orders/track")
def track_order(
    phone: str = "",
    code: str = "",
) -> dict[str, Any]:
    try:
        orders = database.track_orders(phone=phone, code=code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not orders:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    return {"items": orders, "count": len(orders)}


@app.post("/api/auth/login")
def login(data: LoginInput, request: Request) -> dict[str, Any]:
    client_key = request.client.host if request.client else "unknown"
    now = time.time()
    attempts = [
        attempt for attempt in login_attempts.get(client_key, [])
        if now - attempt < LOGIN_WINDOW_SECONDS
    ]
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Aguarde alguns minutos.",
        )

    user = database.authenticate(data.username)
    if user is None or not verify_password(
        data.password, user["salt"], user["password_hash"]
    ):
        attempts.append(now)
        login_attempts[client_key] = attempts
        database.add_audit_log(
            "LOGIN_FAILED",
            f"Usuário informado: {data.username}; IP: {client_key}",
        )
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")

    login_attempts.pop(client_key, None)
    token = new_token()
    session = Session(
        user_id=user["id"],
        name=user["name"],
        role=user["role"],
        expires_at=datetime.now(timezone.utc)
        + timedelta(hours=settings.session_hours),
    )
    sessions[token] = session
    database.add_audit_log(
        "LOGIN_SUCCESS",
        f"IP: {client_key}",
        user_id=session.user_id,
        user_name=session.name,
    )
    return {
        "token": token,
        "user": {
            "userId": session.user_id,
            "name": session.name,
            "role": session.role,
            "expiresAt": session.expires_at.isoformat(),
        },
    }


@app.get("/api/me")
def me(session: Session = Depends(current_session)) -> dict[str, Any]:
    return {
        "user": {
            "userId": session.user_id,
            "name": session.name,
            "role": session.role,
            "expiresAt": session.expires_at.isoformat(),
        }
    }


@app.get("/api/staff/orders")
def staff_orders(_: Session = Depends(current_session)) -> dict[str, Any]:
    return {"items": database.list_orders()}


@app.put("/api/staff/orders/{order_id}/status")
async def update_status(
    order_id: int,
    data: StatusInput,
    session: Session = Depends(current_session),
) -> dict[str, Any]:
    try:
        requested_status = data.status.upper()
        current_order = database.get_order(order_id)

        if current_order is None:
            raise HTTPException(status_code=404, detail="Pedido não encontrado.")

        if requested_status == "DELIVERED" and database.current_cash() is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "O caixa ainda não foi aberto. "
                    "Abra o caixa antes de marcar o pedido como entregue."
                ),
            )

        if (
            requested_status == "DELIVERED"
            and current_order["paymentStatus"] != "PAID"
            and not data.confirmUnpaidDelivery
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "O pagamento deste pedido ainda não foi confirmado. "
                    "Confirme a entrega sem pagamento para continuar."
                ),
            )

        database.update_order_status(order_id, requested_status)
        if requested_status == "CANCELLED":
            database.restore_order_stock(order_id, session.user_id, session.name)
        database.add_audit_log(
            "ORDER_STATUS_CHANGED",
            f"Pedido {order_id}: {requested_status}",
            session.user_id,
            session.name,
        )
        order = database.get_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Pedido não encontrado.")

        if requested_status == "DELIVERED" and order["paymentStatus"] != "PAID":
            database.add_audit_log(
                "UNPAID_ORDER_DELIVERED",
                f"Pedido {order['code']} entregue sem pagamento confirmado",
                session.user_id,
                session.name,
            )

        await realtime.broadcast("ORDER_STATUS_CHANGED", order)
        return order
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/staff/orders/{order_id}/payment")
async def payment(
    order_id: int,
    data: PaymentInput,
    session: Session = Depends(current_session),
) -> dict[str, Any]:
    try:
        database.register_payment(order_id, data.method)
        database.add_audit_log(
            "PAYMENT_CONFIRMED",
            f"Pedido {order_id}; método {data.method.upper()}",
            session.user_id,
            session.name,
        )
        order = database.get_order(order_id) or {}
        await realtime.broadcast("PAYMENT_CONFIRMED", order)
        return order
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/staff/cash/current")
def cash_current(_: Session = Depends(current_session)) -> dict[str, Any]:
    return {"cash": database.current_cash()}


@app.post("/api/staff/cash/open", status_code=201)
def cash_open(
    data: CashInput,
    session: Session = Depends(current_session),
) -> dict[str, Any]:
    try:
        database.open_cash(session.user_id, data.valueCents)
        database.add_audit_log(
            "CASH_OPENED",
            f"Valor inicial: {data.valueCents}",
            session.user_id,
            session.name,
        )
        return {"cash": database.current_cash()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/staff/cash/close")
def cash_close(
    data: CashInput,
    session: Session = Depends(current_session),
) -> dict[str, bool]:
    try:
        database.close_cash(session.user_id, data.valueCents)
        database.add_audit_log(
            "CASH_CLOSED",
            f"Valor contado: {data.valueCents}",
            session.user_id,
            session.name,
        )
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/admin/products")
def admin_products(_: Session = Depends(admin_session)) -> dict[str, Any]:
    return {"items": database.list_products()}


@app.post("/api/admin/products", status_code=201)
def admin_create_product(
    data: ProductInput,
    session: Session = Depends(admin_session),
) -> dict[str, Any]:
    try:
        product_id = database.create_product(data.model_dump())
        database.add_audit_log(
            "PRODUCT_CREATED",
            f"Produto {product_id}: {data.name}",
            session.user_id,
            session.name,
        )
        return next(
            item for item in database.list_products() if item["id"] == product_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/admin/products/{product_id}")
def admin_update_product(
    product_id: int,
    data: ProductInput,
    session: Session = Depends(admin_session),
) -> dict[str, bool]:
    try:
        database.update_product(product_id, data.model_dump())
        database.add_audit_log(
            "PRODUCT_UPDATED",
            f"Produto {product_id}: {data.name}",
            session.user_id,
            session.name,
        )
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/admin/products/{product_id}")
def admin_delete_product(
    product_id: int,
    session: Session = Depends(admin_session),
) -> dict[str, bool]:
    database.delete_product(product_id)
    database.add_audit_log(
        "PRODUCT_DELETED_OR_DISABLED",
        f"Produto {product_id}",
        session.user_id,
        session.name,
    )
    return {"ok": True}


@app.post("/api/admin/demo/order", status_code=201)
async def admin_create_demo_order(
    session: Session = Depends(admin_session),
) -> dict[str, Any]:
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Modo demonstração desativado.")
    products = database.list_products(public_only=True)
    if not products:
        raise HTTPException(status_code=400, detail="Nenhum produto disponível.")
    first = products[0]
    second = products[1] if len(products) > 1 else products[0]
    order = database.create_order({
        "customer": {
            "name": "Cliente Demonstração",
            "phone": "11999990000",
        },
        "items": [
            {"productId": first["id"], "quantity": 2},
            {"productId": second["id"], "quantity": 1},
        ],
        "paymentMethod": "PIX",
        "notes": "Pedido criado automaticamente no modo demonstração.",
    })
    database.add_audit_log(
        "DEMO_ORDER_CREATED",
        order["code"],
        session.user_id,
        session.name,
    )
    await realtime.broadcast("ORDER_CREATED", order)
    return order


@app.get("/api/admin/demo/status")
def admin_demo_status(
    _: Session = Depends(admin_session),
) -> dict[str, bool]:
    return {"enabled": settings.demo_mode}


@app.get("/api/admin/dashboard")
def admin_dashboard(_: Session = Depends(admin_session)) -> dict[str, Any]:
    return {"metrics": database.dashboard_metrics(), "cash": database.current_cash()}


@app.get("/api/admin/sales")
def admin_sales(code: str = "", customer: str = "", phone: str = "", status: str = "", payment_method: str = "", payment_status: str = "", start_date: str = "", end_date: str = "", _: Session = Depends(admin_session)) -> dict[str, Any]:
    items = database.list_sales(code, customer, phone, status, payment_method, payment_status, start_date, end_date)
    return {"items": items, "count": len(items)}


@app.get("/api/admin/sales/export.csv")
def admin_sales_export(code: str = "", customer: str = "", phone: str = "", status: str = "", payment_method: str = "", payment_status: str = "", start_date: str = "", end_date: str = "", _: Session = Depends(admin_session)) -> StreamingResponse:
    items = database.list_sales(code, customer, phone, status, payment_method, payment_status, start_date, end_date, 1000)
    output = io.StringIO(); writer = csv.writer(output, delimiter=";")
    writer.writerow(["Código","Cliente","Telefone","Status","Pagamento","Forma","Total","Criado em"])
    for order in items:
        writer.writerow([order["code"],order["customer"]["name"],order["customer"]["phone"],order["status"],order["paymentStatus"],order["paymentMethod"],f'{order["totalCents"]/100:.2f}'.replace('.',','),order["createdAt"]])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition":"attachment; filename=vendas.csv"})


@app.get("/api/staff/cash/history")
def staff_cash_history(_: Session = Depends(current_session)) -> dict[str, Any]:
    return {"items": database.cash_history()}


@app.post("/api/staff/cash/supply", status_code=201)
def staff_cash_supply(data: CashMovementInput, session: Session = Depends(current_session)) -> dict[str, Any]:
    try:
        mid=database.add_cash_movement("SUPPLY",data.valueCents,data.description)
        database.add_audit_log("CASH_SUPPLY",f"Movimentação {mid}; valor {data.valueCents}",session.user_id,session.name)
        return {"ok":True,"cash":database.current_cash()}
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@app.post("/api/staff/cash/withdrawal", status_code=201)
def staff_cash_withdrawal(data: CashMovementInput, session: Session = Depends(current_session)) -> dict[str, Any]:
    try:
        mid=database.add_cash_movement("WITHDRAWAL",data.valueCents,data.description)
        database.add_audit_log("CASH_WITHDRAWAL",f"Movimentação {mid}; valor {data.valueCents}",session.user_id,session.name)
        return {"ok":True,"cash":database.current_cash()}
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@app.get("/api/admin/customers")
def admin_customers(query: str = "", _: Session = Depends(admin_session)) -> dict[str, Any]:
    items = database.list_customers(query=query)
    return {"items": items, "count": len(items)}

@app.get("/api/admin/audit")
def admin_audit(
    action: str = "", user_name: str = "", start_date: str = "",
    end_date: str = "", limit: int = 200,
    _: Session = Depends(admin_session),
) -> dict[str, Any]:
    items = database.recent_audit_logs(
        limit=limit, action=action, user_name=user_name,
        start_date=start_date, end_date=end_date,
    )
    return {"items": items, "count": len(items)}

@app.get("/api/admin/stock")
def admin_stock(_: Session = Depends(admin_session)) -> dict[str, Any]:
    return {"summary": database.stock_summary(), "products": database.list_products(), "movements": database.list_stock_movements()}

@app.post("/api/admin/stock/movements", status_code=201)
async def admin_stock_movement(data: StockMovementInput, session: Session = Depends(admin_session)) -> dict[str, Any]:
    try:
        result=database.adjust_stock(data.productId,data.quantity,data.movementType,data.reason,session.user_id,session.name)
        database.add_audit_log("STOCK_MOVEMENT",f"Produto {result['productName']}; quantidade {data.quantity}; saldo {result['balance']}",session.user_id,session.name)
        await realtime.broadcast("STOCK_UPDATED",result)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@app.get("/api/admin/finance/summary")
def admin_finance_summary(
    start_date: str = "",
    end_date: str = "",
    _: Session = Depends(admin_session),
) -> dict[str, Any]:
    return database.financial_summary(start_date, end_date)


@app.get("/api/admin/finance/expenses")
def admin_finance_expenses(
    category: str = "",
    payment_method: str = "",
    start_date: str = "",
    end_date: str = "",
    query: str = "",
    _: Session = Depends(admin_session),
) -> dict[str, Any]:
    items = database.list_expenses(
        category, payment_method, start_date, end_date, query
    )
    return {"items": items, "count": len(items)}


@app.post("/api/admin/finance/expenses", status_code=201)
async def admin_create_expense(
    data: ExpenseInput,
    session: Session = Depends(admin_session),
) -> dict[str, Any]:
    try:
        expense_id = database.create_expense(
            data.description, data.category, data.paymentMethod,
            data.valueCents, data.expenseDate, data.notes,
            session.user_id, session.name,
        )
        database.add_audit_log(
            "EXPENSE_CREATED",
            f"Despesa {expense_id}: {data.description}; valor {data.valueCents}",
            session.user_id,
            session.name,
        )
        await realtime.broadcast("FINANCE_UPDATED", {"id": expense_id})
        return {"id": expense_id}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/admin/finance/expenses/{expense_id}")
async def admin_delete_expense(
    expense_id: int,
    session: Session = Depends(admin_session),
) -> dict[str, bool]:
    try:
        database.delete_expense(expense_id)
        database.add_audit_log(
            "EXPENSE_DELETED",
            f"Despesa {expense_id} removida",
            session.user_id,
            session.name,
        )
        await realtime.broadcast("FINANCE_UPDATED", {"id": expense_id})
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/admin/reports")
def admin_reports(
    start_date: str = "",
    end_date: str = "",
    _: Session = Depends(admin_session),
) -> dict[str, Any]:
    return database.business_report(
        start_date=start_date,
        end_date=end_date,
    )


@app.get("/api/admin/reports/export.csv")
def admin_reports_export(
    start_date: str = "",
    end_date: str = "",
    _: Session = Depends(admin_session),
) -> StreamingResponse:
    report = database.business_report(
        start_date=start_date,
        end_date=end_date,
    )

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    summary = report["summary"]
    writer.writerow(["RELATÓRIO GERENCIAL"])
    writer.writerow(["Data inicial", start_date or "Todas"])
    writer.writerow(["Data final", end_date or "Todas"])
    writer.writerow([])
    writer.writerow(["Indicador", "Valor"])
    writer.writerow(["Pedidos", summary["totalOrders"]])
    writer.writerow([
        "Receita",
        f"{summary['revenueCents'] / 100:.2f}".replace(".", ","),
    ])
    writer.writerow([
        "Despesas",
        f"{summary['expenseCents'] / 100:.2f}".replace(".", ","),
    ])
    writer.writerow([
        "Resultado líquido",
        f"{summary['netCents'] / 100:.2f}".replace(".", ","),
    ])
    writer.writerow([
        "Ticket médio",
        f"{summary['averageTicketCents'] / 100:.2f}".replace(".", ","),
    ])
    writer.writerow(["Cancelamentos", summary["cancelledOrders"]])
    writer.writerow(["Taxa de cancelamento (%)", summary["cancellationRate"]])
    writer.writerow([])

    writer.writerow(["PRODUTOS MAIS VENDIDOS"])
    writer.writerow(["Produto", "Quantidade", "Total"])
    for item in report["topProducts"]:
        writer.writerow([
            item["name"],
            item["quantity"],
            f"{item['totalCents'] / 100:.2f}".replace(".", ","),
        ])

    writer.writerow([])
    writer.writerow(["VENDAS POR DIA"])
    writer.writerow(["Data", "Pedidos", "Receita"])
    for item in report["daily"]:
        writer.writerow([
            item["date"],
            item["orders"],
            f"{item['revenueCents'] / 100:.2f}".replace(".", ","),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                "attachment; filename=relatorio_gerencial.csv"
        },
    )


@app.get("/api/admin/system/status")
def admin_system_status(
    _: Session = Depends(admin_session),
) -> dict[str, Any]:
    return {
        "system": system_info(settings.database_path, "1.0.1"),
        "database": database.statistics(),
        "databaseIntegrity": database_integrity(settings.database_path),
        "cash": database.current_cash(),
        "services": {
            "api": "ONLINE",
            "database": "ONLINE",
            "webInterface": "ONLINE",
            "pixIntegration": "MANUAL",
            "printer": "NOT_CONFIGURED",
        },
        "environment": settings.environment,
    }


@app.get("/api/admin/system/logs")
def admin_system_logs(
    limit: int = 100,
    _: Session = Depends(admin_session),
) -> dict[str, Any]:
    return {"items": database.recent_audit_logs(limit)}


@app.get("/api/admin/system/backups")
def admin_backups(
    _: Session = Depends(admin_session),
) -> dict[str, Any]:
    return {"items": list_backups(settings.backups_dir)}


@app.post("/api/admin/system/backups", status_code=201)
def admin_create_backup(
    session: Session = Depends(admin_session),
) -> dict[str, Any]:
    try:
        backup = create_backup(settings.database_path, settings.backups_dir)
        database.add_audit_log(
            "BACKUP_CREATED",
            backup.name,
            session.user_id,
            session.name,
        )
        return {"name": backup.name, "size": backup.stat().st_size}
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/admin/system/backups/{name}")
def admin_download_backup(
    name: str,
    _: Session = Depends(admin_session),
) -> FileResponse:
    try:
        path = safe_backup_path(settings.backups_dir, name)
        return FileResponse(
            path,
            media_type="application/octet-stream",
            filename=path.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/atendimento", include_in_schema=False)
def atendimento_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "atendimento.html")


@app.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/sistema", include_in_schema=False)
def system_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "sistema.html")


@app.get("/sobre", include_in_schema=False)
def about_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "sobre.html")


# Compatibilidade temporária com URLs antigas.
@app.get("/login.html", include_in_schema=False)
def login_page_legacy() -> FileResponse:
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/atendimento.html", include_in_schema=False)
def atendimento_page_legacy() -> FileResponse:
    return FileResponse(STATIC_DIR / "atendimento.html")


@app.get("/admin.html", include_in_schema=False)
def admin_page_legacy() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=False,
    )
