from models import get_db, Well
import sys

def run():
    db = next(get_db())
    well_id = 2
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        print(f"Well {well_id} not found.")
        return
    
    print(f"Attempting to delete {well.name}...")
    try:
        db.delete(well)
        db.commit()
        print("Success!")
    except Exception as e:
        db.rollback()
        print(f"Fail: {e}")

if __name__ == "__main__":
    run()
