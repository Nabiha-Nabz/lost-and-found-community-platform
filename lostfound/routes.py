from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, or_
from werkzeug.utils import secure_filename

from .decorators import roles_required
from .extensions import db
from .forms import CATEGORIES, ClaimForm, ItemForm, LoginForm, ProfileForm, RegistrationForm
from .models import ActivityLog, Claim, Item, ItemImage, Notification, User, utcnow


main = Blueprint("main", __name__)


def log_action(action, entity_type=None, entity_id=None, details=None, user=None):
    actor = user or (current_user if current_user.is_authenticated else None)
    db.session.add(ActivityLog(user_id=actor.id if actor else None, action=action, entity_type=entity_type, entity_id=entity_id, details=details))


def notify(user_id, message, link=None):
    db.session.add(Notification(user_id=user_id, message=message, link=link))


def save_images(files, item):
    saved = []
    for upload in files or []:
        if not upload or not upload.filename:
            continue
        extension = Path(secure_filename(upload.filename)).suffix.lower()
        filename = f"{uuid4().hex}{extension}"
        target = Path(current_app.config["UPLOAD_FOLDER"]) / filename
        try:
            upload.save(target)
            with Image.open(target) as image:
                image.verify()
        except (UnidentifiedImageError, OSError):
            target.unlink(missing_ok=True)
            raise ValueError("One of the uploaded files is not a valid image.")
        item.images.append(ItemImage(filename=f"uploads/{filename}"))
        saved.append(target)
    return saved


def role_dashboard_url(user):
    return url_for(f"main.{user.role}_dashboard")


@main.app_context_processor
def inject_globals():
    unread = 0
    if current_user.is_authenticated:
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return {"categories": CATEGORIES, "unread_notifications": unread}


@main.route("/")
def index():
    recent_items = Item.query.filter_by(approval_status="Approved").order_by(Item.created_at.desc()).limit(6).all()
    stats = {
        "reports": Item.query.count(),
        "active": Item.query.filter_by(approval_status="Approved", status="Active").count(),
        "resolved": Item.query.filter_by(status="Resolved").count(),
    }
    return render_template("index.html", recent_items=recent_items, stats=stats)


@main.route("/about")
def about():
    return render_template("content.html", page="about")


@main.route("/how-it-works")
def how_it_works():
    return render_template("content.html", page="how")


@main.route("/items")
def items():
    query = Item.query.filter_by(approval_status="Approved")
    q = request.args.get("q", "").strip()
    if q:
        term = f"%{q}%"
        query = query.filter(or_(Item.title.ilike(term), Item.description.ilike(term), Item.brand.ilike(term), Item.location_name.ilike(term)))
    if request.args.get("type") in {"lost", "found"}:
        query = query.filter_by(item_type=request.args["type"])
    if request.args.get("category") in CATEGORIES:
        query = query.filter_by(category=request.args["category"])
    location = request.args.get("location", "").strip()
    if location:
        query = query.filter(Item.location_name.ilike(f"%{location}%"))
    sort = request.args.get("sort", "newest")
    ordering = Item.created_at.asc() if sort == "oldest" else (Item.date_lost_found.desc() if sort == "event" else Item.created_at.desc())
    pagination = query.order_by(ordering).paginate(page=request.args.get("page", 1, type=int), per_page=9, error_out=False)
    return render_template("items.html", pagination=pagination, items=pagination.items)


@main.route("/items/<int:item_id>")
def item_detail(item_id):
    item = db.get_or_404(Item, item_id)
    privileged = current_user.is_authenticated and (current_user.role == "admin" or current_user.id == item.created_by)
    if item.approval_status != "Approved" and not privileged:
        abort(404)
    if item.approval_status == "Approved":
        item.view_count += 1
        db.session.commit()
    existing_claim = None
    if current_user.is_authenticated and current_user.role == "buyer":
        existing_claim = Claim.query.filter_by(item_id=item.id, claimant_id=current_user.id).first()
    return render_template("item_detail.html", item=item, claim_form=ClaimForm(), existing_claim=existing_claim, privileged=privileged)


@main.route("/map")
def map_page():
    return render_template("map.html")


@main.route("/api/map-items")
def map_items():
    approved = Item.query.filter(Item.approval_status == "Approved", Item.status != "Closed", Item.latitude.isnot(None), Item.longitude.isnot(None)).all()
    return jsonify([{"id": i.id, "title": i.title, "category": i.category, "type": i.item_type, "location": i.location_name, "lat": round(i.latitude, 3), "lng": round(i.longitude, 3), "url": url_for("main.item_detail", item_id=i.id)} for i in approved])


@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(role_dashboard_url(current_user))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(func.lower(User.email) == form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data) and user.is_active_account:
            login_user(user, remember=form.remember.data)
            user.last_login = utcnow()
            log_action("login", "user", user.id, user=user)
            db.session.commit()
            flash(f"Welcome back, {user.full_name.split()[0]}.", "success")
            return redirect(role_dashboard_url(user))
        flash("Incorrect email or password, or the account is inactive.", "danger")
    return render_template("auth/login.html", form=form)


@main.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))


@main.route("/signup")
def signup_roles():
    return render_template("auth/role_select.html")


@main.route("/signup/<role>", methods=["GET", "POST"])
def signup(role):
    if role not in {"admin", "seller", "buyer"}:
        abort(404)
    form = RegistrationForm()
    if form.validate_on_submit():
        if role == "admin" and form.admin_code.data != current_app.config["ADMIN_REGISTRATION_CODE"]:
            form.admin_code.errors.append("The administrator registration code is incorrect.")
        else:
            user = User(full_name=form.full_name.data.strip(), email=form.email.data.strip().lower(), phone=form.phone.data.strip(), role=role)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            log_action("account_created", "user", user.id, f"{role} account", user=user)
            db.session.commit()
            flash("Account created successfully. You can now sign in.", "success")
            return redirect(url_for("main.login"))
    return render_template("auth/signup.html", form=form, role=role)


@main.route("/seller/dashboard")
@login_required
@roles_required("seller")
def seller_dashboard():
    own_items = Item.query.filter_by(created_by=current_user.id).order_by(Item.created_at.desc()).all()
    item_ids = [item.id for item in own_items]
    claims = Claim.query.filter(Claim.item_id.in_(item_ids)).order_by(Claim.created_at.desc()).limit(6).all() if item_ids else []
    stats = {"posts": len(own_items), "pending": sum(i.approval_status == "Pending" for i in own_items), "active": sum(i.status == "Active" for i in own_items), "claims": Claim.query.filter(Claim.item_id.in_(item_ids)).count() if item_ids else 0, "resolved": sum(i.status == "Resolved" for i in own_items)}
    return render_template("dashboard.html", role="seller", stats=stats, items=own_items[:6], claims=claims)


@main.route("/buyer/dashboard")
@login_required
@roles_required("buyer")
def buyer_dashboard():
    claims = Claim.query.filter_by(claimant_id=current_user.id).order_by(Claim.created_at.desc()).all()
    recent_items = Item.query.filter_by(approval_status="Approved", status="Active").order_by(Item.created_at.desc()).limit(6).all()
    stats = {"claims": len(claims), "pending": sum(c.status == "Pending" for c in claims), "approved": sum(c.status == "Approved" for c in claims), "rejected": sum(c.status == "Rejected" for c in claims)}
    return render_template("dashboard.html", role="buyer", stats=stats, claims=claims, items=recent_items)


@main.route("/admin/dashboard")
@login_required
@roles_required("admin")
def admin_dashboard():
    stats = {"users": User.query.count(), "sellers": User.query.filter_by(role="seller").count(), "buyers": User.query.filter_by(role="buyer").count(), "reports": Item.query.count(), "pending_reports": Item.query.filter_by(approval_status="Pending").count(), "active": Item.query.filter_by(status="Active", approval_status="Approved").count(), "pending_claims": Claim.query.filter_by(status="Pending").count(), "resolved": Item.query.filter_by(status="Resolved").count()}
    items = Item.query.order_by(Item.created_at.desc()).limit(8).all()
    claims = Claim.query.order_by(Claim.created_at.desc()).limit(8).all()
    activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
    return render_template("dashboard.html", role="admin", stats=stats, items=items, claims=claims, activity=activity)


@main.route("/items/new", methods=["GET", "POST"])
@login_required
@roles_required("seller", "admin")
def create_item():
    form = ItemForm()
    if form.validate_on_submit():
        item = Item(title=form.title.data.strip(), description=form.description.data.strip(), item_type=form.item_type.data, category=form.category.data, color=form.color.data.strip(), brand=form.brand.data.strip(), date_lost_found=form.date_lost_found.data, location_name=form.location_name.data.strip(), latitude=form.latitude.data, longitude=form.longitude.data, private_identifying_details=form.private_identifying_details.data.strip(), created_by=current_user.id, approval_status="Pending")
        db.session.add(item)
        db.session.flush()
        try:
            save_images(form.photos.data, item)
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            return render_template("item_form.html", form=form, item=None)
        log_action("item_submitted", "item", item.id, item.title)
        db.session.commit()
        flash("Your item report has been submitted for admin approval.", "success")
        return redirect(url_for("main.item_detail", item_id=item.id))
    return render_template("item_form.html", form=form, item=None)


@main.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("seller", "admin")
def edit_item(item_id):
    item = db.get_or_404(Item, item_id)
    if current_user.role != "admin" and item.created_by != current_user.id:
        abort(403)
    form = ItemForm(obj=item)
    if form.validate_on_submit():
        for field in ["item_type", "title", "category", "description", "color", "brand", "date_lost_found", "location_name", "latitude", "longitude", "private_identifying_details"]:
            setattr(item, field, getattr(form, field).data)
        if current_user.role != "admin":
            item.approval_status = "Pending"
        try:
            save_images(form.photos.data, item)
        except ValueError as error:
            db.session.rollback(); flash(str(error), "danger"); return render_template("item_form.html", form=form, item=item)
        log_action("item_edited", "item", item.id, item.title)
        db.session.commit()
        flash("Report updated successfully.", "success")
        return redirect(url_for("main.item_detail", item_id=item.id))
    return render_template("item_form.html", form=form, item=item)


@main.route("/items/<int:item_id>/delete", methods=["POST"])
@login_required
@roles_required("seller", "admin")
def delete_item(item_id):
    item = db.get_or_404(Item, item_id)
    if current_user.role != "admin" and item.created_by != current_user.id:
        abort(403)
    for image in item.images:
        if image.filename.startswith("uploads/"):
            (Path(current_app.static_folder) / image.filename).unlink(missing_ok=True)
    log_action("item_deleted", "item", item.id, item.title)
    db.session.delete(item); db.session.commit()
    flash("The report has been deleted.", "info")
    return redirect(role_dashboard_url(current_user))


@main.route("/items/<int:item_id>/claim", methods=["POST"])
@login_required
@roles_required("buyer")
def submit_claim(item_id):
    item = db.get_or_404(Item, item_id)
    form = ClaimForm()
    if item.approval_status != "Approved" or item.status not in {"Active", "Claim Pending"}:
        abort(403)
    if Claim.query.filter_by(item_id=item.id, claimant_id=current_user.id).first():
        flash("You have already submitted a claim for this item.", "warning")
    elif form.validate_on_submit():
        claim = Claim(item_id=item.id, claimant_id=current_user.id, ownership_answer=form.ownership_answer.data.strip(), additional_details=form.additional_details.data.strip())
        item.status = "Claim Pending"
        db.session.add(claim); db.session.flush()
        notify(item.created_by, f"A new ownership claim was submitted for {item.title}.", url_for("main.item_detail", item_id=item.id))
        log_action("claim_submitted", "claim", claim.id, item.title)
        db.session.commit(); flash("Claim submitted successfully.", "success")
    else:
        flash("Please provide a detailed ownership answer.", "danger")
    return redirect(url_for("main.item_detail", item_id=item.id))


@main.route("/admin/reports")
@login_required
@roles_required("admin")
def admin_reports():
    status = request.args.get("status", "")
    query = Item.query
    if status in {"Pending", "Approved", "Rejected"}:
        query = query.filter_by(approval_status=status)
    return render_template("admin/list.html", kind="reports", records=query.order_by(Item.created_at.desc()).all())


@main.route("/admin/reports/<int:item_id>/<decision>", methods=["POST"])
@login_required
@roles_required("admin")
def review_report(item_id, decision):
    if decision not in {"approve", "reject"}: abort(404)
    item = db.get_or_404(Item, item_id)
    item.approval_status = "Approved" if decision == "approve" else "Rejected"
    if decision == "reject": item.status = "Closed"
    notify(item.created_by, f"Your report '{item.title}' was {item.approval_status.lower()}.", url_for("main.item_detail", item_id=item.id))
    log_action(f"item_{decision}d", "item", item.id, item.title)
    db.session.commit(); flash(f"Report {item.approval_status.lower()}.", "success")
    return redirect(request.referrer or url_for("main.admin_reports"))


@main.route("/admin/claims")
@login_required
@roles_required("admin")
def admin_claims():
    status = request.args.get("status", "")
    query = Claim.query
    if status in {"Pending", "Approved", "Rejected"}: query = query.filter_by(status=status)
    return render_template("admin/list.html", kind="claims", records=query.order_by(Claim.created_at.desc()).all())


@main.route("/admin/claims/<int:claim_id>")
@login_required
@roles_required("admin")
def claim_review(claim_id):
    return render_template("admin/claim_review.html", claim=db.get_or_404(Claim, claim_id))


@main.route("/admin/claims/<int:claim_id>/<decision>", methods=["POST"])
@login_required
@roles_required("admin")
def decide_claim(claim_id, decision):
    if decision not in {"approve", "reject"}: abort(404)
    claim = db.get_or_404(Claim, claim_id)
    if claim.status != "Pending":
        flash("This claim has already been reviewed.", "warning"); return redirect(url_for("main.claim_review", claim_id=claim.id))
    claim.status = "Approved" if decision == "approve" else "Rejected"
    claim.admin_notes = request.form.get("admin_notes", "").strip()
    claim.reviewed_at = utcnow(); claim.reviewed_by = current_user.id
    if decision == "approve":
        claim.item.status = "Resolved"; claim.item.resolved_at = utcnow()
        for competitor in Claim.query.filter(Claim.item_id == claim.item_id, Claim.id != claim.id, Claim.status == "Pending"):
            competitor.status = "Rejected"; competitor.reviewed_at = utcnow(); competitor.reviewed_by = current_user.id
            notify(competitor.claimant_id, f"Your claim for {claim.item.title} was closed because another claim was approved.")
    elif not Claim.query.filter(Claim.item_id == claim.item_id, Claim.id != claim.id, Claim.status == "Pending").first():
        claim.item.status = "Active"
    notify(claim.claimant_id, f"Your claim for {claim.item.title} was {claim.status.lower()}.", url_for("main.item_detail", item_id=claim.item_id))
    notify(claim.item.created_by, f"A claim for {claim.item.title} was {claim.status.lower()}.", url_for("main.item_detail", item_id=claim.item_id))
    log_action(f"claim_{decision}d", "claim", claim.id, claim.item.title)
    db.session.commit(); flash(f"Claim {claim.status.lower()}.", "success")
    return redirect(url_for("main.claim_review", claim_id=claim.id))


@main.route("/admin/users")
@login_required
@roles_required("admin")
def admin_users():
    q = request.args.get("q", "").strip()
    query = User.query
    if q: query = query.filter(or_(User.full_name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    if request.args.get("role") in {"admin", "seller", "buyer"}: query = query.filter_by(role=request.args["role"])
    return render_template("admin/list.html", kind="users", records=query.order_by(User.created_at.desc()).all())


@main.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@roles_required("admin")
def toggle_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own administrator account.", "warning")
    else:
        user.is_active_account = not user.is_active_account
        log_action("user_status_changed", "user", user.id, f"active={user.is_active_account}")
        db.session.commit(); flash("User status updated.", "success")
    return redirect(url_for("main.admin_users"))


@main.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        if form.new_password.data:
            if not form.current_password.data or not current_user.check_password(form.current_password.data):
                form.current_password.errors.append("Enter your correct current password.")
                return render_template("profile.html", form=form)
            current_user.set_password(form.new_password.data)
        current_user.full_name = form.full_name.data.strip(); current_user.phone = form.phone.data.strip()
        log_action("profile_updated", "user", current_user.id)
        db.session.commit(); flash("Profile updated successfully.", "success")
        return redirect(url_for("main.profile"))
    return render_template("profile.html", form=form)


@main.route("/notifications")
@login_required
def notifications():
    records = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template("notifications.html", records=records)


@main.route("/notifications/read", methods=["POST"])
@login_required
def read_notifications():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit(); flash("Notifications marked as read.", "success")
    return redirect(url_for("main.notifications"))
