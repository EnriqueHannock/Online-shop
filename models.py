from datetime import datetime
from extensions import db


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    description = db.Column(db.Text, default="")
    material = db.Column(db.String(150), default="")
    price_mwk = db.Column(db.Float, nullable=False)
    sizes = db.Column(db.String(200), default="S,M,L,XL")  # comma separated
    colors = db.Column(db.String(200), default="")  # comma separated
    image = db.Column(db.String(300), default="")  # main image filename
    gallery = db.Column(db.Text, default="")  # comma separated extra filenames
    production_time = db.Column(db.String(100), default="5-7 days")
    delivery_estimate = db.Column(db.String(100), default="2-4 days (local)")
    stock = db.Column(db.Integer, default=10)
    trending = db.Column(db.Boolean, default=False)
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviews = db.relationship("Review", backref="product", lazy=True, cascade="all, delete-orphan")

    def price_usd(self, rate):
        return round(self.price_mwk / rate, 2)

    def sizes_list(self):
        return [s.strip() for s in self.sizes.split(",") if s.strip()]

    def colors_list(self):
        return [c.strip() for c in self.colors.split(",") if c.strip()]

    def gallery_list(self):
        return [g.strip() for g in self.gallery.split(",") if g.strip()]

    def avg_rating(self):
        if not self.reviews:
            return 0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)

    def to_dict(self, rate):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "material": self.material,
            "price_mwk": self.price_mwk,
            "price_usd": self.price_usd(rate),
            "sizes": self.sizes_list(),
            "colors": self.colors_list(),
            "image": self.image,
            "gallery": self.gallery_list(),
            "production_time": self.production_time,
            "delivery_estimate": self.delivery_estimate,
            "stock": self.stock,
            "trending": self.trending,
            "featured": self.featured,
            "rating": self.avg_rating(),
            "review_count": len(self.reviews),
        }


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_ref = db.Column(db.String(20), unique=True, nullable=False)
    customer_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(150), default="")
    address = db.Column(db.String(300), default="")
    city = db.Column(db.String(100), default="")
    country = db.Column(db.String(100), default="Malawi")
    items_json = db.Column(db.Text, nullable=False)  # JSON list of {product_id,name,size,color,qty,price}
    subtotal_mwk = db.Column(db.Float, nullable=False)
    delivery_fee_mwk = db.Column(db.Float, default=0)
    total_mwk = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), default="")
    payment_proof = db.Column(db.String(300), default="")
    status = db.Column(db.String(30), default="Pending Payment")
    # Pending Payment -> Payment Confirmed -> In Production/Packed -> Shipped -> Delivered -> Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def items(self):
        import json
        return json.loads(self.items_json)


class CustomDesignRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(150), default="")
    event_type = db.Column(db.String(100), default="")
    preferred_design = db.Column(db.Text, default="")
    measurements = db.Column(db.Text, default="")
    budget_range = db.Column(db.String(100), default="")
    deadline = db.Column(db.String(50), default="")
    notes = db.Column(db.Text, default="")
    inspiration_image = db.Column(db.String(300), default="")
    status = db.Column(db.String(30), default="New")  # New -> Reviewed -> Quoted -> In Production -> Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(150), default="")
    booking_type = db.Column(db.String(50), default="WhatsApp Consultation")
    preferred_date = db.Column(db.String(50), default="")
    preferred_time = db.Column(db.String(50), default="")
    notes = db.Column(db.Text, default="")
    status = db.Column(db.String(30), default="Pending")  # Pending -> Approved -> Rejected -> Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    customer_name = db.Column(db.String(150), nullable=False)
    rating = db.Column(db.Integer, default=5)
    comment = db.Column(db.Text, default="")
    image = db.Column(db.String(300), default="")
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class InspirationPost(db.Model):
    """Admin-only fashion inspiration feed post (Pinterest/Instagram style)."""
    id = db.Column(db.Integer, primary_key=True)
    media = db.Column(db.String(300), nullable=False)  # image or video filename
    media_type = db.Column(db.String(10), default="image")  # image | video
    caption = db.Column(db.Text, default="")
    hashtags = db.Column(db.String(300), default="")
    linked_product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True)
    pinned = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    linked_product = db.relationship("Product")


class Subscriber(db.Model):
    """Newsletter / marketing contact captured at checkout or on-site."""
    id = db.Column(db.Integer, primary_key=True)
    contact = db.Column(db.String(150), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
