import firebase_admin_init  # ensures firebase_admin.initialize_app() has run
from firebase_admin import firestore

db = firestore.client()
