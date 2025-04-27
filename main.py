from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from models import User, Shop, Rating
from schemas import UserCreate, ShopCreate, RatingCreate
from database import db
from utils import generate_qr_code, is_within_distance
from security import hash_password
import shutil
import os
from datetime import datetime, timedelta
from collections import defaultdict  # ✅ Correctly moved to top

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all websites (for now)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods like GET, POST
    allow_headers=["*"],  # Allow all headers
)

# Create upload folder if not exists
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# User Registration
@app.post("/register")
def register_user(user: UserCreate):
    if user.email in db['users']:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = hash_password(user.password)
    db['users'][user.email] = User(
        email=user.email,
        password=hashed_pw,
        user_type=user.user_type
    )
    return {"message": "User registered successfully"}

# Shop Registration
@app.post("/add_shop")
def add_shop(shop: ShopCreate):
    if shop.owner_email not in db['users']:
        raise HTTPException(status_code=404, detail="Owner not found")

    shop_id = f"shop_{len(db['shops'])+1}"
    qr_image_path = generate_qr_code(shop_id)
    
    db['shops'][shop_id] = Shop(
        id=shop_id,
        name=shop.name,
        location=shop.location,
        latitude=shop.latitude,
        longitude=shop.longitude,
        food_type=shop.food_type,
        contact=shop.contact,
        owner_email=shop.owner_email,
        qr_code_path=qr_image_path
    )

    return {"message": "Shop added successfully", "shop_id": shop_id, "qr_code_path": qr_image_path}

# Shop Listing
@app.get("/shops")
def list_shops():
    return list(db['shops'].values())

# Rating a Shop
@app.post("/rate_shop")
def rate_shop(rating: RatingCreate):
    if rating.customer_email not in db['users']:
        raise HTTPException(status_code=404, detail="Customer not found")
    if rating.shop_id not in db['shops']:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    shop = db['shops'][rating.shop_id]

    # Distance checking
    if not is_within_distance(
        rating.customer_lat,
        rating.customer_lon,
        shop.latitude,
        shop.longitude
    ):
        raise HTTPException(status_code=403, detail="You are too far from the shop to rate")

    # One rating per shop per customer per week
    one_week_ago = datetime.now() - timedelta(days=7)

    for r in db['ratings']:
        if (
            r.customer_email == rating.customer_email and
            r.shop_id == rating.shop_id
        ):
            if hasattr(r, 'timestamp') and r.timestamp > one_week_ago:
                raise HTTPException(
                    status_code=403,
                    detail="You can only rate the same shop once per week."
                )

    # Save rating with timestamp
    rating_data = rating.dict()
    rating_data['timestamp'] = datetime.now()
    db['ratings'].append(Rating(**rating_data))

    return {"message": "Rating submitted successfully"}

# Upload Shop Photo
@app.post("/upload_shop_photo")
def upload_shop_photo(file: UploadFile = File(...)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"message": "Shop photo uploaded successfully", "file_path": file_location}

# Get Shop Scorecard (Weekly/Monthly/Yearly)
@app.get("/shops/{shop_id}/scorecard")
def get_shop_scorecard(shop_id: str):
    if shop_id not in db['shops']:
        raise HTTPException(status_code=404, detail="Shop not found")

    now = datetime.now()
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)
    one_year_ago = now - timedelta(days=365)

    scores = {
        "weekly": defaultdict(list),
        "monthly": defaultdict(list),
        "yearly": defaultdict(list),
    }

    for r in db['ratings']:
        if r.shop_id == shop_id:
            timestamp = getattr(r, 'timestamp', None)
            if not timestamp:
                continue  # skip old ratings without timestamp

            if timestamp > one_week_ago:
                scores['weekly']['food_quality'].append(r.food_quality)
                scores['weekly']['hygiene'].append(r.hygiene)
                scores['weekly']['service'].append(r.service)
                scores['weekly']['value_for_money'].append(r.value_for_money)
                scores['weekly']['overall_experience'].append(r.overall_experience)

            if timestamp > one_month_ago:
                scores['monthly']['food_quality'].append(r.food_quality)
                scores['monthly']['hygiene'].append(r.hygiene)
                scores['monthly']['service'].append(r.service)
                scores['monthly']['value_for_money'].append(r.value_for_money)
                scores['monthly']['overall_experience'].append(r.overall_experience)

            if timestamp > one_year_ago:
                scores['yearly']['food_quality'].append(r.food_quality)
                scores['yearly']['hygiene'].append(r.hygiene)
                scores['yearly']['service'].append(r.service)
                scores['yearly']['value_for_money'].append(r.value_for_money)
                scores['yearly']['overall_experience'].append(r.overall_experience)

    def calculate_average(values):
        if not values:
            return 0
        return round(sum(values) / len(values), 2)

    result = {}
    for period in ['weekly', 'monthly', 'yearly']:
        result[period] = {
            "food_quality": calculate_average(scores[period]['food_quality']),
            "hygiene": calculate_average(scores[period]['hygiene']),
            "service": calculate_average(scores[period]['service']),
            "value_for_money": calculate_average(scores[period]['value_for_money']),
            "overall_experience": calculate_average(scores[period]['overall_experience']),
        }

    return result
@app.get("/rankings")
def get_shop_rankings(
    location: str = None, 
    city: str = None, 
    state: str = None, 
    country: str = "India", 
    period: str = "weekly"
):
    now = datetime.now()
    if period == "weekly":
        cutoff_date = now - timedelta(days=7)
    elif period == "monthly":
        cutoff_date = now - timedelta(days=30)
    elif period == "yearly":
        cutoff_date = now - timedelta(days=365)
    else:
        raise HTTPException(status_code=400, detail="Invalid period. Choose 'weekly', 'monthly' or 'yearly'.")

    shop_scores = {}

    for shop_id, shop in db['shops'].items():
        if location and shop.location.lower() != location.lower():
            continue  # skip if location filter doesn't match

        # In real app: match city, state, country from extra fields
        # For now we assume all shops are in "India" (simplified)

        ratings = [
            r for r in db['ratings'] 
            if r.shop_id == shop_id and hasattr(r, 'timestamp') and r.timestamp > cutoff_date
        ]

        if ratings:
            avg_overall_experience = sum(r.overall_experience for r in ratings) / len(ratings)
            shop_scores[shop_id] = round(avg_overall_experience, 2)

    # Sort shops by score (high to low)
    ranked_shops = sorted(shop_scores.items(), key=lambda item: item[1], reverse=True)

    # Prepare Top 10 results
    top_shops = []
    for shop_id, score in ranked_shops[:10]:
        shop = db['shops'][shop_id]
        top_shops.append({
            "shop_id": shop.id,
            "name": shop.name,
            "location": shop.location,
            "overall_experience": score
        })

    return top_shops
@app.get("/top_reviewers")
def get_top_reviewers():
    now = datetime.now()
    one_month_ago = now - timedelta(days=30)

    reviewer_counts = {}

    for r in db['ratings']:
        if hasattr(r, 'timestamp') and r.timestamp > one_month_ago:
            reviewer_counts[r.customer_email] = reviewer_counts.get(r.customer_email, 0) + 1

    # Sort reviewers by count (high to low)
    top_reviewers = sorted(reviewer_counts.items(), key=lambda item: item[1], reverse=True)

    # Prepare Top 5 reviewers
    result = []
    for email, count in top_reviewers[:5]:
        result.append({
            "email": email,
            "ratings_count": count,
            "badge": "Top Reviewer" if count >= 5 else "Active Reviewer"
        })

    return result
@app.get("/top_shops")
def get_top_rated_shops():
    now = datetime.now()
    one_month_ago = now - timedelta(days=30)

    shop_rating_counts = {}

    for r in db['ratings']:
        if hasattr(r, 'timestamp') and r.timestamp > one_month_ago:
            shop_rating_counts[r.shop_id] = shop_rating_counts.get(r.shop_id, 0) + 1

    # Sort shops by number of ratings
    top_shops = sorted(shop_rating_counts.items(), key=lambda item: item[1], reverse=True)

    # Prepare Top 5 shops
    result = []
    for shop_id, count in top_shops[:5]:
        shop = db['shops'].get(shop_id)
        if shop:
            result.append({
                "shop_id": shop.id,
                "name": shop.name,
                "location": shop.location,
                "ratings_received": count,
                "badge": "Most Rated Shop" if count >= 5 else "Popular Shop"
            })

    return result
@app.post("/donate_to_shop")
def donate_to_shop(shop_id: str, amount: int):
    if shop_id not in db['shops']:
        raise HTTPException(status_code=404, detail="Shop not found")

    if amount not in [10, 20, 50, 100]:
        raise HTTPException(status_code=400, detail="Invalid donation amount. Choose 10, 20, 50, or 100 INR.")

    shop = db['shops'][shop_id]
    if not hasattr(shop, 'donations_received'):
        shop.donations_received = 0

    shop.donations_received += amount

    return {"message": f"Donation of ₹{amount} successful to shop {shop.name}!"}
@app.post("/boost_shop")
def boost_shop(shop_id: str):
    if shop_id not in db['shops']:
        raise HTTPException(status_code=404, detail="Shop not found")

    shop = db['shops'][shop_id]
    shop.boost_expiry = datetime.now() + timedelta(days=7)

    return {"message": f"Shop {shop.name} has been boosted for 7 days!"}
from fastapi import Form

# Upload Photo Post
@app.post("/upload_post")
async def upload_post(caption: str = Form(...), image: UploadFile = File(...)):
    post_id = f"post_{len(db['posts'])+1}"
    upload_path = f"uploads/{post_id}_{image.filename}"
    
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    db['posts'].append({
        "id": post_id,
        "image_url": f"http://127.0.0.1:8000/{upload_path}",
        "caption": caption,
    })

    return {"message": "Post uploaded successfully", "post_id": post_id}


# Fetch All Posts
@app.get("/posts")
def get_posts():
    return db['posts']
from fastapi.staticfiles import StaticFiles

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
