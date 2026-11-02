import os
import pytest
from app import create_app, db, Product, Adjustment


@pytest.fixture
def app(tmp_path):
    # TEST_DATABASE_URL must refer only to a disposable test database.
    application = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": os.getenv("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")})
    with application.app_context():
        db.drop_all()
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


def post(client, path, **data):
    client.get("/")
    with client.session_transaction() as session:
        data["csrf"] = session["csrf"]
    return client.post(path, data=data)


def test_inventory(app):
    client = app.test_client()
    assert post(client, "/products", code="abc", name="Widget").status_code == 302
    assert post(client, "/products", code="ABC", name="Duplicate").status_code == 409
    assert post(client, "/products/1/adjustments", quantity="10", note="Delivery").status_code == 302
    assert post(client, "/products/1/adjustments", quantity="-11", note="Too many").status_code == 409
    assert post(client, "/products/1/adjustments", quantity="-3", note="Sold").status_code == 302
    with app.app_context():
        assert db.session.get(Product, 1).stock == 7
        assert db.session.query(Adjustment).count() == 2
    assert b"Delivery" in client.get("/products/1").data
    assert b"7" in app.test_client().get("/products/1").data


@pytest.mark.parametrize("quantity", ["0", "abc", "1000001", "1.5"])
def test_bad_quantity(app, quantity):
    client = app.test_client()
    post(client, "/products", code="a", name="A")
    assert post(client, "/products/1/adjustments", quantity=quantity, note="test").status_code == 400


def test_health_and_csrf(app, monkeypatch):
    client = app.test_client()
    monkeypatch.setenv("APP_VERSION", "test-revision")
    assert client.get("/version").json == {"version": "test-revision"}
    assert client.get("/health/ready").status_code == 200
    assert client.post("/products", data={"code": "a", "name": "A"}).status_code == 400
    with app.app_context():
        db.drop_all()
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 503


def test_schema_initialization_retains_data(app):
    client = app.test_client()
    post(client, "/products", code="keep", name="Keep me")
    for _ in range(2):
        assert app.test_cli_runner().invoke(args=["init-db"]).exit_code == 0
    with app.app_context():
        assert db.session.query(Product).count() == 1


def test_concurrent_deductions(app):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    client = app.test_client()
    post(client, "/products", code="last", name="Last unit")
    post(client, "/products/1/adjustments", quantity="1", note="Received")
    barrier = Barrier(2)

    def deduct():
        with app.test_client() as other:
            barrier.wait(timeout=10)
            return post(other, "/products/1/adjustments", quantity="-1", note="Concurrent sale").status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: deduct(), range(2)))
    assert sorted(results) == [302, 409]
    with app.app_context():
        assert db.session.get(Product, 1).stock == 0
        assert db.session.query(Adjustment).count() == 2


def test_aws_database_url_fetches_secret_at_runtime(monkeypatch):
    import app as module
    import json
    captured = {}

    class Secrets:
        def get_secret_value(self, **kwargs):
            captured.update(kwargs)
            return {"SecretString": json.dumps({"username": "user", "password": "p@ss:/word"})}

    monkeypatch.setenv("DB_SECRET_ARN", "arn:example:secret")
    monkeypatch.setenv("DB_HOST", "db.example")
    monkeypatch.setenv("AWS_REGION", "us-east-2")
    monkeypatch.setattr(module.boto3, "client", lambda *args, **kwargs: Secrets())
    url = module.database_url()
    assert captured == {"SecretId": "arn:example:secret"}
    assert url.password == "p@ss:/word" and url.host == "db.example"
    assert url.query["sslmode"] == "verify-full"
