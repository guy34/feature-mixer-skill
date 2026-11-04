# PyShop models (SQLAlchemy, illustrative)
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey

class Product:  # table products
    id = Column(Integer, primary_key=True); name = Column(String); price = Column(Numeric)

class Cart:     # table carts
    id = Column(Integer, primary_key=True); user_id = Column(Integer)

class CartItem: # table cart_items
    id = Column(Integer, primary_key=True); cart_id = Column(Integer, ForeignKey("carts.id")); product_id = Column(Integer); quantity = Column(Integer)
