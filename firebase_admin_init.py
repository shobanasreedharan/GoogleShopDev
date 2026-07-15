import firebase_admin
from firebase_admin import credentials

# Service account key downloaded from:
# Firebase Console > Project Settings > Service Accounts > Generate new private key
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
