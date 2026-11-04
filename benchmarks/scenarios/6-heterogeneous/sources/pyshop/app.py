# PyShop routes (Flask, illustrative)
from flask import Flask
app = Flask(__name__)

@app.get("/api/products")            # browse the catalog, filter by category
def catalog(): ...

@app.post("/api/cart/items")         # add a product to the cart: {"product_id": int, "quantity": int}
def add_to_cart(): ...
