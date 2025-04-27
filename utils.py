import qrcode
import os
from geopy.distance import geodesic

# Function to generate QR Code
def generate_qr_code(shop_id):
    data = f"http://127.0.0.1:8000/shops/{shop_id}"
    img = qrcode.make(data)

    if not os.path.exists("qr_codes"):
        os.makedirs("qr_codes")

    path = f"qr_codes/{shop_id}.png"
    img.save(path)
    return path

# Function to check if customer is within allowed distance
def is_within_distance(customer_lat, customer_lon, shop_lat, shop_lon, max_distance_meters=100):
    customer_location = (customer_lat, customer_lon)
    shop_location = (shop_lat, shop_lon)
    
    distance = geodesic(customer_location, shop_location).meters

    print(f"Distance between customer and shop: {distance:.2f} meters")  # ✅ Useful for checking

    return distance <= max_distance_meters
