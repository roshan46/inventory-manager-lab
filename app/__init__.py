"""Small inventory application; runtime AWS credentials never enter Terraform state."""
import os
import json
import secrets
from datetime import datetime, timezone

import boto3
import click
from flask import Flask, abort, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, URL, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

db = SQLAlchemy()


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    __table_args__ = (CheckConstraint("stock >= 0", name="nonnegative_stock"),)


class Adjustment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


def database_url():
    if os.getenv("DB_SECRET_ARN"):
        value = boto3.client("secretsmanager", region_name=os.environ["AWS_REGION"]).get_secret_value(
            SecretId=os.environ["DB_SECRET_ARN"])
        secret = json.loads(value["SecretString"])
        return URL.create("postgresql+psycopg", username=secret["username"], password=secret["password"],
                          host=os.environ["DB_HOST"], port=5432, database="inventory",
                          query={"sslmode": "verify-full", "sslrootcert": "/srv/rds-ca.pem", "connect_timeout": "5"})
    return os.getenv("DATABASE_URL", "sqlite:///inventory.db")


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.getenv("APP_SECRET", "local-practice-only"),
                      SQLALCHEMY_DATABASE_URI=(config or {}).get("SQLALCHEMY_DATABASE_URI") or database_url(),
                      SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
                      MAX_CONTENT_LENGTH=16384, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    app.config.update(config or {})
    db.init_app(app)

    @app.before_request
    def csrf():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(32)
        if request.method == "POST" and not secrets.compare_digest(session["csrf"], request.form.get("csrf", "")):
            abort(400, "Invalid form token; reload the page")

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        click.echo("Schema ready (existing data retained).")

    @app.get("/")
    def index():
        return render_template("index.html", products=db.session.scalars(db.select(Product).order_by(Product.code)),
                               version=os.getenv("APP_VERSION", "local"))

    @app.post("/products")
    def create_product():
        code, name = request.form.get("code", "").strip().upper(), request.form.get("name", "").strip()
        if not code or len(code) > 40 or not name or len(name) > 120:
            abort(400, "Code (1-40 characters) and name (1-120 characters) are required")
        db.session.add(Product(code=code, name=name, stock=0))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, "Product code already exists")
        return redirect(url_for("index"))

    @app.get("/products/<int:product_id>")
    def detail(product_id):
        product = db.get_or_404(Product, product_id)
        history = db.session.scalars(db.select(Adjustment).where(Adjustment.product_id == product_id).order_by(Adjustment.id.desc()))
        return render_template("detail.html", product=product, history=history)

    @app.post("/products/<int:product_id>/adjustments")
    def adjust(product_id):
        db.get_or_404(Product, product_id)
        try:
            quantity = int(request.form.get("quantity", ""))
        except ValueError:
            abort(400, "Quantity must be an integer")
        note = request.form.get("note", "").strip()
        if quantity == 0 or abs(quantity) > 1000000 or not note or len(note) > 200:
            abort(400, "Supply a nonzero quantity up to 1,000,000 and a note up to 200 characters")
        # Atomic conditional UPDATE prevents concurrent deductions from overselling.
        changed = db.session.execute(update(Product).where(Product.id == product_id,
            Product.stock + quantity >= 0, Product.stock + quantity <= 2147483647).values(stock=Product.stock + quantity))
        if changed.rowcount != 1:
            db.session.rollback()
            abort(409, "Adjustment would exceed stock limits")
        db.session.add(Adjustment(product_id=product_id, quantity=quantity, note=note))
        db.session.commit()
        return redirect(url_for("detail", product_id=product_id))

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        try:
            db.session.execute(text("SELECT id FROM product LIMIT 1"))
            return {"status": "ready"}
        except SQLAlchemyError:
            db.session.rollback()
            return {"status": "unavailable"}, 503

    @app.get("/version")
    def version():
        return {"version": os.getenv("APP_VERSION", "local")}

    return app
