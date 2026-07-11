import os
import json
import uuid
import random
import string
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, abort, send_from_directory
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from extensions import db
from models import (
    Product, Order, CustomDesignRequest, Booking,
    Review, InspirationPost, Subscriber
)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    for folder in [
        app.config["PRODUCT_UPLOAD_FOLDER"],
        app.config["POST_UPLOAD_FOLDER"],
        app.config["PROOF_UPLOAD_FOLDER"],
    ]:
        os.makedirs(folder, exist_ok=True)

    with app.app_context():
        db.create_all()

    register_context_processors(app)
    register_public_routes(app)
    register_api_routes(app)
    register_admin_routes(app)

    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def save_upload(file_storage, folder):
    if not file_storage or file_storage.filename == "":
        return ""
    if not allowed_file(file_storage.filename):
        return ""
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(folder, fname))
    return fname


def generate_order_ref():
    return "ND-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=7))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


CATEGORIES = [
    "Men's Wear", "Women's Wear", "Kids' Wear", "Corporate Wear",
    "Traditional Wear", "Wedding Wear", "Hoodies", "Jackets",
    "Dresses", "Suits", "T-Shirts", "Sportswear", "Custom Orders",
]

PAYMENT_METHODS = [
    {"id": "airtel_money", "label": "Airtel Money", "group": "Mobile Money"},
    {"id": "tnm_mpamba", "label": "TNM Mpamba", "group": "Mobile Money"},
    {"id": "bank_transfer", "label": "Bank Transfer", "group": "Bank"},
    {"id": "visa_mastercard", "label": "Visa / Mastercard", "group": "International"},
    {"id": "paypal", "label": "PayPal", "group": "International"},
    {"id": "binance_pay", "label": "Binance Pay", "group": "Crypto"},
    {"id": "usdt", "label": "USDT (Crypto)", "group": "Crypto"},
]


# ---------------------------------------------------------------------------
# Context processors (available in every template)
# ---------------------------------------------------------------------------

def register_context_processors(app):
    @app.context_processor
    def inject_globals():
        return {
            "STORE_NAME": app.config["STORE_NAME"],
            "STORE_TAGLINE": app.config["STORE_TAGLINE"],
            "WHATSAPP_NUMBER": app.config["WHATSAPP_NUMBER"],
            "CATEGORIES": CATEGORIES,
            "USD_RATE": app.config["USD_TO_MWK_RATE"],
        }


# ---------------------------------------------------------------------------
# Public storefront routes
# ---------------------------------------------------------------------------

def register_public_routes(app):

    @app.route("/")
    def home():
        trending = Product.query.filter_by(trending=True).order_by(Product.created_at.desc()).limit(8).all()
        featured = Product.query.filter_by(featured=True).order_by(Product.created_at.desc()).limit(6).all()
        posts = InspirationPost.query.order_by(
            InspirationPost.pinned.desc(), InspirationPost.created_at.desc()
        ).limit(12).all()
        reviews = Review.query.filter_by(approved=True).order_by(Review.created_at.desc()).limit(6).all()
        return render_template(
            "index.html", trending=trending, featured=featured, posts=posts, reviews=reviews
        )

    @app.route("/shop")
    def shop():
        category = request.args.get("category", "")
        q = request.args.get("q", "")
        sort = request.args.get("sort", "newest")
        query = Product.query
        if category:
            query = query.filter_by(category=category)
        if q:
            like = f"%{q}%"
            query = query.filter(
                db.or_(Product.name.ilike(like), Product.description.ilike(like), Product.material.ilike(like))
            )
        if sort == "price_low":
            query = query.order_by(Product.price_mwk.asc())
        elif sort == "price_high":
            query = query.order_by(Product.price_mwk.desc())
        elif sort == "trending":
            query = query.order_by(Product.trending.desc(), Product.created_at.desc())
        else:
            query = query.order_by(Product.created_at.desc())
        products = query.all()
        return render_template(
            "shop.html", products=products, active_category=category, q=q, sort=sort
        )

    @app.route("/product/<int:product_id>")
    def product_detail(product_id):
        product = Product.query.get_or_404(product_id)
        related = Product.query.filter(
            Product.category == product.category, Product.id != product.id
        ).limit(4).all()
        reviews = Review.query.filter_by(product_id=product.id, approved=True).order_by(
            Review.created_at.desc()
        ).all()
        return render_template("product.html", product=product, related=related, reviews=reviews)

    @app.route("/inspiration")
    def inspiration():
        posts = InspirationPost.query.order_by(
            InspirationPost.pinned.desc(), InspirationPost.created_at.desc()
        ).all()
        return render_template("inspiration.html", posts=posts)

    @app.route("/cart")
    def cart():
        return render_template("cart.html")

    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():
        if request.method == "POST":
            items = json.loads(request.form.get("cart_items", "[]"))
            if not items:
                flash("Your cart is empty.", "error")
                return redirect(url_for("shop"))

            subtotal = sum(float(i["price"]) * int(i["qty"]) for i in items)
            city = request.form.get("city", "")
            country = request.form.get("country", "Malawi")
            delivery_fee = 0 if country.lower() == "malawi" else 25000
            total = subtotal + delivery_fee

            proof_file = request.files.get("payment_proof")
            proof_name = save_upload(proof_file, app.config["PROOF_UPLOAD_FOLDER"])

            order = Order(
                order_ref=generate_order_ref(),
                customer_name=request.form.get("name", ""),
                phone=request.form.get("phone", ""),
                email=request.form.get("email", ""),
                address=request.form.get("address", ""),
                city=city,
                country=country,
                items_json=json.dumps(items),
                subtotal_mwk=subtotal,
                delivery_fee_mwk=delivery_fee,
                total_mwk=total,
                payment_method=request.form.get("payment_method", ""),
                payment_proof=proof_name,
                status="Pending Payment",
            )
            db.session.add(order)
            db.session.commit()
            return redirect(url_for("order_confirmation", order_ref=order.order_ref))

        payment_info = {
            "airtel_money": app.config["AIRTEL_MONEY_NUMBER"],
            "tnm_mpamba": app.config["TNM_MPAMBA_NUMBER"],
        }
        return render_template("checkout.html", payment_methods=PAYMENT_METHODS, payment_info=payment_info)

    @app.route("/order-confirmation/<order_ref>")
    def order_confirmation(order_ref):
        order = Order.query.filter_by(order_ref=order_ref).first_or_404()
        payment_info = {
            "airtel_money": Config.AIRTEL_MONEY_NUMBER,
            "tnm_mpamba": Config.TNM_MPAMBA_NUMBER,
            "bank_transfer": f"{Config.BANK_NAME} — {Config.BANK_ACCOUNT_NAME} — {Config.BANK_ACCOUNT_NUMBER}",
            "binance_pay": Config.BINANCE_PAY_ID,
            "usdt": Config.USDT_WALLET_ADDRESS,
        }
        return render_template("order_confirmation.html", order=order, payment_info=payment_info)

    @app.route("/track-order", methods=["GET", "POST"])
    def track_order():
        order = None
        searched = False
        if request.method == "POST":
            searched = True
            ref_or_phone = request.form.get("ref_or_phone", "").strip()
            order = Order.query.filter(
                db.or_(Order.order_ref == ref_or_phone, Order.phone == ref_or_phone)
            ).order_by(Order.created_at.desc()).first()
        return render_template("track_order.html", order=order, searched=searched)

    @app.route("/custom-design", methods=["GET", "POST"])
    def custom_design():
        if request.method == "POST":
            image_file = request.files.get("inspiration_image")
            image_name = save_upload(image_file, app.config["POST_UPLOAD_FOLDER"])
            req = CustomDesignRequest(
                name=request.form.get("name", ""),
                phone=request.form.get("phone", ""),
                email=request.form.get("email", ""),
                event_type=request.form.get("event_type", ""),
                preferred_design=request.form.get("preferred_design", ""),
                measurements=request.form.get("measurements", ""),
                budget_range=request.form.get("budget_range", ""),
                deadline=request.form.get("deadline", ""),
                notes=request.form.get("notes", ""),
                inspiration_image=image_name,
            )
            db.session.add(req)
            db.session.commit()
            flash("Your custom design request has been received! We'll contact you shortly.", "success")
            return redirect(url_for("custom_design"))
        return render_template("custom_design.html")

    @app.route("/book-consultation", methods=["GET", "POST"])
    def book_consultation():
        if request.method == "POST":
            booking = Booking(
                name=request.form.get("name", ""),
                phone=request.form.get("phone", ""),
                email=request.form.get("email", ""),
                booking_type=request.form.get("booking_type", "WhatsApp Consultation"),
                preferred_date=request.form.get("preferred_date", ""),
                preferred_time=request.form.get("preferred_time", ""),
                notes=request.form.get("notes", ""),
            )
            db.session.add(booking)
            db.session.commit()
            flash("Your consultation has been requested! We'll confirm with you soon.", "success")
            return redirect(url_for("book_consultation"))
        return render_template("book_consultation.html")

    @app.route("/about")
    def about():
        return render_template("about.html")


# ---------------------------------------------------------------------------
# JSON / AJAX API routes (search, size AI, recommendations, chatbot)
# ---------------------------------------------------------------------------

def register_api_routes(app):

    @app.route("/api/search")
    def api_search():
        q = request.args.get("q", "").strip()
        if len(q) < 2:
            return jsonify([])
        like = f"%{q}%"
        products = Product.query.filter(
            db.or_(Product.name.ilike(like), Product.category.ilike(like), Product.material.ilike(like))
        ).limit(8).all()
        rate = app.config["USD_TO_MWK_RATE"]
        return jsonify([p.to_dict(rate) for p in products])

    @app.route("/api/size-recommendation", methods=["POST"])
    def api_size_recommendation():
        data = request.get_json(force=True)
        try:
            height = float(data.get("height_cm", 0))
            weight = float(data.get("weight_kg", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Enter valid height and weight."}), 400
        body_type = data.get("body_type", "average")

        bmi = weight / ((height / 100) ** 2) if height else 0
        if bmi < 18.5:
            base = 0
        elif bmi < 23:
            base = 1
        elif bmi < 26:
            base = 2
        elif bmi < 29:
            base = 3
        elif bmi < 32:
            base = 4
        else:
            base = 5
        sizes = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]
        if body_type == "athletic":
            base = min(base + 1, len(sizes) - 1)
        elif body_type == "slim":
            base = max(base - 1, 0)
        size = sizes[min(base, len(sizes) - 1)]
        return jsonify({
            "recommended_size": size,
            "note": "This is a starting estimate — for tailored or custom pieces we always confirm with your exact measurements."
        })

    @app.route("/api/newsletter", methods=["POST"])
    def api_newsletter():
        contact = request.get_json(force=True).get("contact", "").strip()
        if not contact:
            return jsonify({"error": "Please enter an email or phone number."}), 400
        if not Subscriber.query.filter_by(contact=contact).first():
            db.session.add(Subscriber(contact=contact))
            db.session.commit()
        return jsonify({"ok": True})

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        """Server-side proxy to the Claude API so the API key never reaches the browser."""
        api_key = app.config.get("ANTHROPIC_API_KEY")
        if not api_key:
            return jsonify({
                "reply": "Our AI assistant isn't fully set up yet — please message us directly on WhatsApp and our team will help right away!"
            })

        payload = request.get_json(force=True)
        user_message = (payload.get("message") or "").strip()
        history = payload.get("history", [])[-8:]  # keep last 8 turns for context
        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        trending = Product.query.filter_by(trending=True).limit(6).all()
        rate = app.config["USD_TO_MWK_RATE"]
        catalog_snippet = "; ".join(
            f"{p.name} ({p.category}, {p.price_mwk:,.0f} MWK)" for p in trending
        ) or "Catalog is being updated — recommend browsing the Shop page."

        system_prompt = (
            f"You are Aria, the friendly AI shopping assistant for {app.config['STORE_NAME']}, "
            f"a premium Malawian fashion and tailoring brand ({app.config['STORE_TAGLINE']}). "
            "Help customers with sizing questions, delivery, custom tailoring, payment options "
            "(Airtel Money, TNM Mpamba, bank transfer, Visa/Mastercard, PayPal, Binance Pay, USDT), "
            "and general fashion advice. Keep replies short (2-4 sentences), warm, and helpful. "
            "If you don't know specific stock or pricing, suggest the customer check the Shop page "
            "or the WhatsApp button for a human reply. Never invent prices you're not given. "
            f"Some current trending items: {catalog_snippet}. "
            "Do not discuss anything unrelated to Nashe Designs, fashion, or shopping."
        )

        try:
            import urllib.request
            messages = history + [{"role": "user", "content": user_message}]
            body = json.dumps({
                "model": app.config["CHATBOT_MODEL"],
                "max_tokens": 400,
                "system": system_prompt,
                "messages": messages,
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            reply_text = "".join(
                block.get("text", "") for block in result.get("content", []) if block.get("type") == "text"
            ).strip() or "Sorry, could you rephrase that?"
            return jsonify({"reply": reply_text})
        except Exception as exc:  # noqa: BLE001
            app.logger.exception("Chatbot error")
            return jsonify({
                "reply": "I'm having trouble connecting right now — please try again, or reach us on WhatsApp for immediate help."
            })


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

def register_admin_routes(app):

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if username == app.config["ADMIN_USERNAME"] and password == app.config["ADMIN_PASSWORD"]:
                session.permanent = True
                session["is_admin"] = True
                nxt = request.args.get("next") or url_for("admin_dashboard")
                return redirect(nxt)
            flash("Invalid username or password.", "error")
        return render_template("admin/login.html")

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("is_admin", None)
        return redirect(url_for("admin_login"))

    @app.route("/admin")
    @login_required
    def admin_dashboard():
        total_sales = db.session.query(db.func.coalesce(db.func.sum(Order.total_mwk), 0)).filter(
            Order.status != "Cancelled"
        ).scalar()
        total_orders = Order.query.count()
        pending_deliveries = Order.query.filter(
            Order.status.in_(["Payment Confirmed", "In Production", "Shipped"])
        ).count()
        pending_bookings = Booking.query.filter_by(status="Pending").count()
        new_custom_requests = CustomDesignRequest.query.filter_by(status="New").count()
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
        return render_template(
            "admin/dashboard.html",
            total_sales=total_sales,
            total_orders=total_orders,
            pending_deliveries=pending_deliveries,
            pending_bookings=pending_bookings,
            new_custom_requests=new_custom_requests,
            recent_orders=recent_orders,
            product_count=Product.query.count(),
        )

    # --- Products ---
    @app.route("/admin/products")
    @login_required
    def admin_products():
        products = Product.query.order_by(Product.created_at.desc()).all()
        return render_template("admin/products.html", products=products)

    @app.route("/admin/products/new", methods=["GET", "POST"])
    @login_required
    def admin_product_new():
        if request.method == "POST":
            image_name = save_upload(request.files.get("image"), app.config["PRODUCT_UPLOAD_FOLDER"])
            gallery_files = request.files.getlist("gallery")
            gallery_names = [save_upload(f, app.config["PRODUCT_UPLOAD_FOLDER"]) for f in gallery_files]
            gallery_names = [g for g in gallery_names if g]
            product = Product(
                name=request.form.get("name", ""),
                category=request.form.get("category", ""),
                description=request.form.get("description", ""),
                material=request.form.get("material", ""),
                price_mwk=float(request.form.get("price_mwk", 0) or 0),
                sizes=request.form.get("sizes", "S,M,L,XL"),
                colors=request.form.get("colors", ""),
                image=image_name,
                gallery=",".join(gallery_names),
                production_time=request.form.get("production_time", "5-7 days"),
                delivery_estimate=request.form.get("delivery_estimate", "2-4 days"),
                stock=int(request.form.get("stock", 10) or 0),
                trending=bool(request.form.get("trending")),
                featured=bool(request.form.get("featured")),
            )
            db.session.add(product)
            db.session.commit()
            flash("Product added.", "success")
            return redirect(url_for("admin_products"))
        return render_template("admin/product_form.html", product=None, categories=CATEGORIES)

    @app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
    @login_required
    def admin_product_edit(product_id):
        product = Product.query.get_or_404(product_id)
        if request.method == "POST":
            new_image = save_upload(request.files.get("image"), app.config["PRODUCT_UPLOAD_FOLDER"])
            if new_image:
                product.image = new_image
            gallery_files = request.files.getlist("gallery")
            gallery_names = [save_upload(f, app.config["PRODUCT_UPLOAD_FOLDER"]) for f in gallery_files]
            gallery_names = [g for g in gallery_names if g]
            if gallery_names:
                existing = product.gallery_list()
                product.gallery = ",".join(existing + gallery_names)

            product.name = request.form.get("name", product.name)
            product.category = request.form.get("category", product.category)
            product.description = request.form.get("description", product.description)
            product.material = request.form.get("material", product.material)
            product.price_mwk = float(request.form.get("price_mwk", product.price_mwk) or 0)
            product.sizes = request.form.get("sizes", product.sizes)
            product.colors = request.form.get("colors", product.colors)
            product.production_time = request.form.get("production_time", product.production_time)
            product.delivery_estimate = request.form.get("delivery_estimate", product.delivery_estimate)
            product.stock = int(request.form.get("stock", product.stock) or 0)
            product.trending = bool(request.form.get("trending"))
            product.featured = bool(request.form.get("featured"))
            db.session.commit()
            flash("Product updated.", "success")
            return redirect(url_for("admin_products"))
        return render_template("admin/product_form.html", product=product, categories=CATEGORIES)

    @app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
    @login_required
    def admin_product_delete(product_id):
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted.", "success")
        return redirect(url_for("admin_products"))

    # --- Orders ---
    @app.route("/admin/orders")
    @login_required
    def admin_orders():
        status_filter = request.args.get("status", "")
        query = Order.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        orders = query.order_by(Order.created_at.desc()).all()
        statuses = ["Pending Payment", "Payment Confirmed", "In Production", "Shipped", "Delivered", "Cancelled"]
        return render_template("admin/orders.html", orders=orders, statuses=statuses, status_filter=status_filter)

    @app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
    @login_required
    def admin_order_status(order_id):
        order = Order.query.get_or_404(order_id)
        order.status = request.form.get("status", order.status)
        db.session.commit()
        flash(f"Order {order.order_ref} updated to {order.status}.", "success")
        return redirect(url_for("admin_orders"))

    # --- Custom design requests ---
    @app.route("/admin/custom-requests")
    @login_required
    def admin_custom_requests():
        requests_ = CustomDesignRequest.query.order_by(CustomDesignRequest.created_at.desc()).all()
        return render_template("admin/custom_requests.html", requests=requests_)

    @app.route("/admin/custom-requests/<int:req_id>/status", methods=["POST"])
    @login_required
    def admin_custom_request_status(req_id):
        req = CustomDesignRequest.query.get_or_404(req_id)
        req.status = request.form.get("status", req.status)
        db.session.commit()
        return redirect(url_for("admin_custom_requests"))

    # --- Bookings ---
    @app.route("/admin/bookings")
    @login_required
    def admin_bookings():
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        return render_template("admin/bookings.html", bookings=bookings)

    @app.route("/admin/bookings/<int:booking_id>/status", methods=["POST"])
    @login_required
    def admin_booking_status(booking_id):
        booking = Booking.query.get_or_404(booking_id)
        booking.status = request.form.get("status", booking.status)
        db.session.commit()
        return redirect(url_for("admin_bookings"))

    # --- Inspiration feed (CMS) ---
    @app.route("/admin/posts")
    @login_required
    def admin_posts():
        posts = InspirationPost.query.order_by(InspirationPost.created_at.desc()).all()
        products = Product.query.order_by(Product.name).all()
        return render_template("admin/posts.html", posts=posts, products=products)

    @app.route("/admin/posts/new", methods=["POST"])
    @login_required
    def admin_post_new():
        media_file = request.files.get("media")
        media_name = save_upload(media_file, app.config["POST_UPLOAD_FOLDER"])
        if not media_name:
            flash("Please choose an image or video.", "error")
            return redirect(url_for("admin_posts"))
        ext = media_name.rsplit(".", 1)[1].lower()
        media_type = "video" if ext in {"mp4", "mov"} else "image"
        linked_id = request.form.get("linked_product_id") or None
        post = InspirationPost(
            media=media_name,
            media_type=media_type,
            caption=request.form.get("caption", ""),
            hashtags=request.form.get("hashtags", ""),
            linked_product_id=int(linked_id) if linked_id else None,
            pinned=bool(request.form.get("pinned")),
        )
        db.session.add(post)
        db.session.commit()
        flash("Post published to inspiration feed.", "success")
        return redirect(url_for("admin_posts"))

    @app.route("/admin/posts/<int:post_id>/delete", methods=["POST"])
    @login_required
    def admin_post_delete(post_id):
        post = InspirationPost.query.get_or_404(post_id)
        db.session.delete(post)
        db.session.commit()
        return redirect(url_for("admin_posts"))

    # --- Reviews moderation ---
    @app.route("/admin/reviews")
    @login_required
    def admin_reviews():
        reviews = Review.query.order_by(Review.created_at.desc()).all()
        return render_template("admin/reviews.html", reviews=reviews)

    @app.route("/admin/reviews/<int:review_id>/toggle", methods=["POST"])
    @login_required
    def admin_review_toggle(review_id):
        review = Review.query.get_or_404(review_id)
        review.approved = not review.approved
        db.session.commit()
        return redirect(url_for("admin_reviews"))

    @app.route("/admin/reviews/<int:review_id>/delete", methods=["POST"])
    @login_required
    def admin_review_delete(review_id):
        review = Review.query.get_or_404(review_id)
        db.session.delete(review)
        db.session.commit()
        return redirect(url_for("admin_reviews"))


# ---------------------------------------------------------------------------
# CLI: seed demo data
# ---------------------------------------------------------------------------

app = create_app()


@app.cli.command("seed")
def seed():
    """Seed the database with starter categories of demo products (placeholder images).
    Run with: flask --app app seed
    """
    if Product.query.count() > 0:
        print("Products already exist — skipping seed.")
        return

    demo = [
        ("Editorial Wrap Dress", "Dresses", 85000, "Silk-blend", "S,M,L,XL", "Black,Charcoal"),
        ("Tailored Corporate Suit", "Suits", 165000, "Wool-blend", "S,M,L,XL,XXL", "Black,Navy"),
        ("Chitenje Traditional Set", "Traditional Wear", 62000, "Cotton chitenje", "S,M,L,XL", "Multicolor"),
        ("Wedding Gown — Ivory", "Wedding Wear", 320000, "Satin & lace", "XS,S,M,L", "Ivory"),
        ("Classic Oxford Shirt", "Men's Wear", 38000, "Cotton", "S,M,L,XL,XXL", "White,Black"),
        ("Kids' School Uniform Set", "Kids' Wear", 25000, "Poly-cotton", "XS,S,M", "Navy,White"),
        ("Corporate Blazer", "Corporate Wear", 95000, "Wool-blend", "S,M,L,XL", "Black,Charcoal"),
        ("Premium Hoodie", "Hoodies", 32000, "Heavyweight fleece", "S,M,L,XL,XXL", "Black,Beige"),
        ("Utility Jacket", "Jackets", 78000, "Canvas", "S,M,L,XL", "Black,Olive"),
        ("Everyday Essential Tee", "T-Shirts", 15000, "Combed cotton", "S,M,L,XL,XXL", "Black,White,Beige"),
        ("Performance Track Set", "Sportswear", 48000, "Moisture-wick poly", "S,M,L,XL", "Black,Gray"),
        ("Bespoke Custom Piece", "Custom Orders", 0, "Client's choice", "XS,S,M,L,XL,XXL,XXXL", "Made to order"),
    ]
    for i, (name, cat, price, material, sizes, colors) in enumerate(demo):
        db.session.add(Product(
            name=name, category=cat, price_mwk=price, material=material,
            sizes=sizes, colors=colors, description=f"{name} — crafted by Nashe Designs.",
            trending=(i % 3 == 0), featured=(i % 4 == 0), stock=15,
        ))
    db.session.commit()
    print(f"Seeded {len(demo)} demo products. Replace placeholder images via /admin/products.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
