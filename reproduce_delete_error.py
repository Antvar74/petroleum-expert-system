from models import init_db, get_db, Well, Problem, Analysis, Program
import sys

def test_delete():
    db_gen = get_db()
    db = next(db_gen)
    
    # List wells
    wells = db.query(Well).all()
    if not wells:
        print("No wells found to delete.")
        return

    well_to_delete = wells[0]
    well_id = well_to_delete.id
    print(f"Attempting to delete well: {well_to_delete.name} (ID: {well_id})")

    try:
        # Manual cascade delete (same logic as api_main.py)
        # 1. Get all problems
        problems = db.query(Problem).filter(Problem.well_id == well_id).all()
        print(f"Found {len(problems)} problems.")
        
        # 2. Delete analyses for each problem
        for problem in problems:
            count = db.query(Analysis).filter(Analysis.problem_id == problem.id).delete(synchronize_session=False)
            print(f"  Deleted {count} analyses for problem {problem.id}")
            
        # 3. Delete problems
        count = db.query(Problem).filter(Problem.well_id == well_id).delete(synchronize_session=False)
        print(f"Deleted {count} problems.")
        
        # 4. Delete programs (if any)
        count = db.query(Program).filter(Program.well_id == well_id).delete(synchronize_session=False)
        print(f"Deleted {count} programs.")
        
        # 5. Delete well
        db.delete(well_to_delete)
        db.commit()
        print("✅ Well deleted successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during deletion: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_delete()
