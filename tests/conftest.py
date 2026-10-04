import pytest

from config import TestConfig
from lostfound import create_app
from lostfound.extensions import db
from lostfound.seed import seed_database


@pytest.fixture()
def app(tmp_path):
    app = create_app(TestConfig)
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    app.config["UPLOAD_FOLDER"] = upload_dir
    with app.app_context():
        db.create_all()
        seed_database()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password):
    return client.post('/login', data={'email': email, 'password': password}, follow_redirects=False)
