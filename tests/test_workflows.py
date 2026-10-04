from io import BytesIO

from PIL import Image

from lostfound.extensions import db
from lostfound.models import Claim, Item, User
from tests.conftest import login


def image_file():
    stream = BytesIO()
    Image.new('RGB', (60, 60), '#176b5b').save(stream, 'PNG')
    stream.seek(0)
    return stream


def test_seed_is_exact_and_idempotent(app):
    from lostfound.seed import seed_database
    with app.app_context():
        assert User.query.count() == 3
        assert Item.query.count() == 8
        seed_database()
        assert User.query.count() == 3
        assert Item.query.count() == 8


def test_login_redirects_and_authorization(client):
    response = login(client, 'buyer@lostfound.local', 'Buyer@123')
    assert response.status_code == 302 and '/buyer/dashboard' in response.location
    assert client.get('/admin/dashboard').status_code == 403
    client.post('/logout')
    assert login(client, 'seller@lostfound.local', 'wrong').status_code == 200


def test_all_role_dashboards_render(client):
    for email, password, path, heading in [
        ('admin@lostfound.local', 'Admin@123', '/admin/dashboard', b'Admin dashboard'),
        ('seller@lostfound.local', 'Seller@123', '/seller/dashboard', b'Post an item dashboard'),
        ('buyer@lostfound.local', 'Buyer@123', '/buyer/dashboard', b'Claim Item dashboard'),
    ]:
        login(client, email, password)
        response = client.get(path)
        assert response.status_code == 200
        assert heading in response.data
        client.post('/logout')


def test_registration_and_duplicate_email(client, app):
    payload = {'full_name':'New Buyer','email':'new@example.com','phone':'','password':'Password123!','confirm_password':'Password123!','agree':'y'}
    assert client.post('/signup/buyer', data=payload).status_code == 302
    assert client.post('/signup/buyer', data=payload).status_code == 200
    with app.app_context(): assert User.query.filter_by(email='new@example.com', role='buyer').count() == 1


def test_complete_report_claim_resolution_workflow(client, app):
    assert login(client, 'seller@lostfound.local', 'Seller@123').status_code == 302
    response = client.post('/items/new', data={
        'item_type':'found','title':'Test green umbrella','category':'Other','description':'A green folding umbrella found after the workshop.',
        'color':'Green','brand':'RainSafe','date_lost_found':'2026-09-15','location_name':'Community Hall','latitude':'28.61','longitude':'77.21',
        'private_identifying_details':'A short name is written beneath the handle.','photos':(image_file(),'umbrella.png')
    }, content_type='multipart/form-data', follow_redirects=False)
    assert response.status_code == 302
    with app.app_context():
        item = Item.query.filter_by(title='Test green umbrella').one(); item_id=item.id
        assert item.approval_status == 'Pending' and item.images
    client.post('/logout')
    login(client, 'admin@lostfound.local', 'Admin@123')
    assert client.post(f'/admin/reports/{item_id}/approve').status_code == 302
    client.post('/logout')
    login(client, 'buyer@lostfound.local', 'Buyer@123')
    search = client.get('/items?q=green+umbrella')
    assert b'Test green umbrella' in search.data
    assert client.post(f'/items/{item_id}/claim', data={'ownership_answer':'The hidden name under the handle is Taylor and the strap is torn.','additional_details':'Lost near the hall.'}).status_code == 302
    with app.app_context():
        claim = Claim.query.filter_by(item_id=item_id).one(); claim_id=claim.id
        assert claim.status == 'Pending'
    client.post('/logout')
    login(client, 'admin@lostfound.local', 'Admin@123')
    assert client.post(f'/admin/claims/{claim_id}/approve', data={'admin_notes':'Private identifiers are consistent.'}).status_code == 302
    with app.app_context():
        assert db.session.get(Claim, claim_id).status == 'Approved'
        assert db.session.get(Item, item_id).status == 'Resolved'


def test_seller_cannot_edit_another_users_report(client, app):
    with app.app_context():
        other=User(full_name='Other Seller',email='other@example.com',role='seller'); other.set_password('Password123!'); db.session.add(other); db.session.flush()
        item=Item(title='Other item',description='A sufficiently descriptive item report.',item_type='lost',category='Other',color='Blue',date_lost_found=__import__('datetime').date.today(),location_name='Elsewhere',private_identifying_details='A private hidden feature.',created_by=other.id); db.session.add(item); db.session.commit(); item_id=item.id
    login(client, 'seller@lostfound.local', 'Seller@123')
    assert client.get(f'/items/{item_id}/edit').status_code == 403
