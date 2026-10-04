from datetime import date, timedelta

from .extensions import db
from .models import Item, ItemImage, User


DEMO_ITEMS = [
    ("Navy commuter backpack", "found", "Bags", "Navy", "North Ridge", "Toronto Reference Library", 43.6715, -79.3868, "A practical backpack with two main compartments and reflective trim.", "Small stitched initials beneath the inner label.", "seed-backpack.jpg", "Active"),
    ("Brown leather wallet", "lost", "Wallets", "Brown", "Harbor & Co.", "St. Lawrence Market, Toronto", 43.6487, -79.3716, "Slim leather wallet lost during an afternoon visit.", "A faded receipt is tucked behind the card sleeve.", "seed-wallet.jpg", "Active"),
    ("Silver key ring", "found", "Keys", "Silver", "", "Vancouver Public Library", 49.2819, -123.1157, "A set of keys with a simple metal ring was handed in.", "One key has a small green paint mark near its head.", "seed-keys.jpg", "Active"),
    ("Black smartphone", "lost", "Phones", "Black", "Orion", "Nathan Phillips Square, Toronto", 43.6525, -79.3839, "Black smartphone in a protective case, last seen near the public square.", "The lock-screen background and a mark under the case can be described.", "seed-phone.jpg", "Active"),
    ("Wireless earphones case", "found", "Electronics", "White", "SoundPod", "Montreal Central Station", 45.4999, -73.5660, "Charging case with both wireless earphones found after an evening journey.", "A tiny handwritten symbol appears inside the lid.", "seed-earphones.jpg", "Active"),
    ("Student document holder", "lost", "Documents/IDs", "Blue", "", "Calgary Central Library", 51.0456, -114.0576, "Blue document holder containing study materials. Sensitive contents are not shown.", "The owner can identify the course label and inner pocket contents.", "seed-docs.jpg", "Resolved"),
    ("Classic wristwatch", "found", "Accessories", "Black", "Tempo", "Halifax Public Gardens", 44.6457, -63.5819, "Analogue wristwatch with a dark strap found beside a bench.", "There is a short engraving on the reverse.", "seed-watch.jpg", "Active"),
    ("Grey laptop sleeve", "lost", "Laptops/Tablets", "Grey", "Porta", "Ottawa Public Library", 45.4218, -75.6972, "Padded laptop sleeve with front pocket, lost during a workshop.", "The zipper pull and an item inside the front pocket are distinctive.", "seed-sleeve.jpg", "Active"),
]


def seed_database():
    users = {}
    for role, email, password, name in [
        ("admin", "admin@lostfound.local", "Admin@123", "Demo Administrator"),
        ("seller", "seller@lostfound.local", "Seller@123", "Demo Reporter"),
        ("buyer", "buyer@lostfound.local", "Buyer@123", "Demo Seeker"),
    ]:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(full_name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
        users[role] = user

    for index, data in enumerate(DEMO_ITEMS):
        title, kind, category, color, brand, location, lat, lon, description, private, image, status = data
        existing = Item.query.filter_by(title=title, created_by=users["seller"].id).first()
        if not existing:
            item = Item(
                title=title, item_type=kind, category=category, color=color, brand=brand,
                location_name=location, latitude=lat, longitude=lon, description=description,
                private_identifying_details=private, approval_status="Approved", status=status,
                created_by=users["seller"].id, date_lost_found=date.today() - timedelta(days=index + 1)
            )
            db.session.add(item)
            db.session.flush()
            db.session.add(ItemImage(item_id=item.id, filename=f"images/{image}"))
        else:
            existing.location_name = location
            existing.latitude = lat
            existing.longitude = lon
            seeded_image = next((record for record in existing.images if record.filename.startswith("images/")), None)
            if seeded_image:
                seeded_image.filename = f"images/{image}"
    db.session.commit()
