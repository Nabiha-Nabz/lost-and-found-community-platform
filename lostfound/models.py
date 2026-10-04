from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    phone = db.Column(db.String(30))
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    last_login = db.Column(db.DateTime)
    items = db.relationship("Item", backref="creator", lazy=True, foreign_keys="Item.created_by")
    claims = db.relationship("Claim", backref="claimant", lazy=True, foreign_keys="Claim.claimant_id")

    @property
    def is_active(self):
        return self.is_active_account

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    item_type = db.Column(db.String(10), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    color = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(80))
    date_lost_found = db.Column(db.Date, nullable=False)
    location_name = db.Column(db.String(180), nullable=False, index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    private_identifying_details = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="Active", nullable=False, index=True)
    approval_status = db.Column(db.String(30), default="Pending", nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime)
    view_count = db.Column(db.Integer, default=0, nullable=False)
    images = db.relationship("ItemImage", backref="item", lazy=True, cascade="all, delete-orphan")
    claims = db.relationship("Claim", backref="item", lazy=True, cascade="all, delete-orphan")

    @property
    def primary_image(self):
        return self.images[0].filename if self.images else "images/item-default.svg"


class ItemImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Claim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False, index=True)
    claimant_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    ownership_answer = db.Column(db.Text, nullable=False)
    additional_details = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending", nullable=False, index=True)
    admin_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])
    __table_args__ = (db.UniqueConstraint("item_id", "claimant_id", name="uq_item_claimant"),)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    user = db.relationship("User", backref="notifications")


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    user = db.relationship("User")
