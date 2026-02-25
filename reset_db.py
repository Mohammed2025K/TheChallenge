from app import app, db

with app.app_context():
    db.drop_all()
    db.create_all()
    print("The database has been successfully reset.")
