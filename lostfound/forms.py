from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, MultipleFileField
from wtforms import BooleanField, DateField, FloatField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, Optional, Regexp, ValidationError

from .models import User


CATEGORIES = ["Electronics", "Phones", "Laptops/Tablets", "Wallets", "Bags", "Keys", "Documents/IDs", "Jewellery", "Clothing", "Books", "Accessories", "Other"]
EMAIL_VALIDATORS = [DataRequired(), Length(max=255), Regexp(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", message="Enter a valid email address.")]


class LoginForm(FlaskForm):
    email = StringField("Email", validators=EMAIL_VALIDATORS)
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class RegistrationForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=EMAIL_VALIDATORS)
    phone = StringField("Phone (optional)", validators=[Optional(), Length(max=30)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    admin_code = PasswordField("Admin registration code", validators=[Optional()])
    agree = BooleanField("I agree to the privacy and community guidelines", validators=[DataRequired()])
    submit = SubmitField("Create account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("An account already uses this email address.")


class ItemForm(FlaskForm):
    item_type = SelectField("Report type", choices=[("lost", "Lost"), ("found", "Found")], validators=[DataRequired()])
    title = StringField("Title", validators=[DataRequired(), Length(min=4, max=160)])
    category = SelectField("Category", choices=[(c, c) for c in CATEGORIES], validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired(), Length(min=15, max=2000)])
    color = StringField("Color", validators=[DataRequired(), Length(max=50)])
    brand = StringField("Brand (optional)", validators=[Optional(), Length(max=80)])
    date_lost_found = DateField("Date lost or found", validators=[DataRequired()], default=date.today)
    location_name = StringField("General location", validators=[DataRequired(), Length(min=3, max=180)])
    latitude = FloatField("Latitude", validators=[Optional()])
    longitude = FloatField("Longitude", validators=[Optional()])
    photos = MultipleFileField("Photos", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Upload JPG, PNG, or WebP images only.")])
    private_identifying_details = TextAreaField("Private identifying details", validators=[DataRequired(), Length(min=8, max=1000)])
    submit = SubmitField("Submit report")

    def validate_date_lost_found(self, field):
        if field.data and field.data > date.today():
            raise ValidationError("The date cannot be in the future.")

    def validate_latitude(self, field):
        if field.data is not None and not -90 <= field.data <= 90:
            raise ValidationError("Latitude must be between -90 and 90.")

    def validate_longitude(self, field):
        if field.data is not None and not -180 <= field.data <= 180:
            raise ValidationError("Longitude must be between -180 and 180.")


class ClaimForm(FlaskForm):
    ownership_answer = TextAreaField("What private feature proves this item is yours?", validators=[DataRequired(), Length(min=15, max=1500)])
    additional_details = TextAreaField("Additional details", validators=[Optional(), Length(max=1500)])
    submit = SubmitField("Submit ownership claim")


class ProfileForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    phone = StringField("Phone (optional)", validators=[Optional(), Length(max=30)])
    current_password = PasswordField("Current password", validators=[Optional()])
    new_password = PasswordField("New password", validators=[Optional(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm new password", validators=[Optional(), EqualTo("new_password")])
    submit = SubmitField("Save profile")
