from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
from database import db
from sqlalchemy import text
import bcrypt
import uvicorn
from middleware import create_token, verify_token

# Load environment variables
load_dotenv()

# FastAPI instance
app = FastAPI(title="Expense Tracker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- ROOT ROUTE -------------------
@app.get("/")
def welcome():
    return {"message": "Welcome to Expense Tracker API"}

# ------------------- USER SIGNUP -------------------
class User(BaseModel):
    name: str = Field(..., example="Favour")
    email: str = Field(..., example="favour@gmail.com")
    password: str = Field(..., example="1234")

@app.post("/signup")
def signup(data: User):
    try:
        # Check if email already exists
        duplicate_query = text("""
            SELECT * FROM users
            WHERE email = :email
        """)
        existing = db.execute(duplicate_query, {"email": data.email}).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

        # Hash password
        salt = bcrypt.gensalt()
        hashedpassword = bcrypt.hashpw(data.password.encode("utf-8"), salt).decode("utf-8")

        # Insert new user
        query = text("""
            INSERT INTO users (name, email, password)
            VALUES (:name, :email, :password)
        """)
        db.execute(query, {"name": data.name, "email": data.email, "password": hashedpassword})
        db.commit()

        return {
            "message": "User signed up successfully!",
            "data": {"name": data.name, "email": data.email}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------- USER LOGIN -------------------
class Login(BaseModel):
    email: str = Field(..., example="favour@gmail.com")
    password: str = Field(..., example="1234")

@app.post("/login")
def login(data: Login):
    try:
        # Find user by email
        query = text("""
            SELECT * FROM users
            WHERE email = :email
        """)
        result = db.execute(query, {"email": data.email}).mappings().fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="User does not exist")

        # Verify password
        is_valid = bcrypt.checkpw(data.password.encode("utf-8"), result["password"].encode("utf-8"))
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid email or password")

        # Generate token
        token = create_token(
            {"name": result["name"], "email": result["email"], "id": result["id"]},
            int(os.getenv("expiry", "3600"))
        )

        return {
            "message": "User logged in successfully",
            "token": token,
            "userData": {
                "id": result["id"],
                "name": result["name"],
                "email": result["email"]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------- ADD EXPENSE -------------------
class Expense(BaseModel):
    title: str = Field(..., example="Transport fare")
    amount: int = Field(..., example=20000)
    dateinput: str = Field(..., example="2025-10-12")
    category: str = Field(..., example="Transport")
    budget: int = Field(..., example=2000000)

@app.post("/expenses")
def add_expense(input: Expense, user_data=Depends(verify_token)):
    try:
        # Insert expense
        query = text("""
            INSERT INTO expensetracker (user_id, title, amount, dateinput, category, budget)
            VALUES (:user_id, :title, :amount, :dateinput, :category, :budget)
        """)
        db.execute(query, {
            "user_id": user_data["id"],
            "title": input.title,
            "amount": input.amount,
            "dateinput": input.dateinput,
            "category": input.category,
            "budget": input.budget
        })
        db.commit()

        return {
            "message": "Expense added successfully",
            "data": {
                "title": input.title,
                "amount": input.amount,
                "dateinput": input.dateinput,
                "category": input.category,
                "budget": input.budget
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/expenses")
def get_expense(user_data=Depends(verify_token)):
    try:
        query = text("""
            SELECT * FROM expensetracker
            WHERE user_id = :user_id
        """)
        input = db.execute(query, {
            "user_id": user_data["id"]
        }).fetchall()
        db.commit()

        expenses = []

        for item in input:
            expenses.append({
                "title": item.title,
                "amount": item.amount,
                "dateinput": item.dateinput,
                "category": item.category,
                "budget": item.budget
            })

        return {
            "message": "Expense added successfully",
            "data": expenses
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/getuser")
def get_user(user_data=Depends(verify_token)):
    query = text("""
    SELECT * FROM users
    WHERE id = :id
""")
    user = db.execute(query, {"id": user_data["id"]}).fetchone()
    print(user)
    return {
        "user_data": {"id": user.id, "name": user.name, "email": user.email}
    }

@app.delete("/expenses")
def delete_expense(expense_id: int, user_data=Depends(verify_token)):
    try:
        print("Decoded user data:", user_data)

        # --- Validate token data ---
        if not user_data or "id" not in user_data:
            raise HTTPException(status_code=400, detail=str(e))

        # --- Check if expense exists and belongs to the current user ---
        check_query = text("""
            SELECT * FROM expensetracker
            WHERE id = :expense_id AND user_id = :user_id
        """)
        expense = db.execute(check_query, {
            "expense_id": expense_id,
            "user_id": user_data["id"]
        }).fetchone()

        if not expense:
                raise HTTPException(status_code=400, detail=str(e))
                

        # --- Delete the expense ---
        delete_query = text("DELETE FROM expensetracker WHERE id = :expense_id")
        db.execute(delete_query, {"expense_id": expense_id})
        db.commit()

        return {"message": "Expense deleted successfully"}

    except HTTPException:
        raise  # re-raise for clean status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/expenses/{expense_id}")
def update_expense(expense_id: int, data: dict, user_data=Depends(verify_token)):
    try:
        # Verify user authentication
        if not user_data or "id" not in user_data:
            raise HTTPException(status_code=401, detail="User authentication failed")

        check_query = text("""
            SELECT * FROM expensetracker
            WHERE id = :expense_id AND user_id = :user_id
        """)
        expense = db.execute(check_query, {
            "expense_id": expense_id,
            "user_id": user_data["id"]
        }).fetchone()

        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found or not authorized to update")

        title = data.get("title", expense.title)
        amount = data.get("amount", expense.amount)
        dateinput = data.get("dateinput", expense.dateinput)
        category = data.get("category", expense.category)
        budget = data.get("budget", expense.budget)

        update_query = text("""
            UPDATE expensetracker
            SET title = :title,
                amount = :amount,
                dateinput = :dateinput,
                category = :category,
                budget = :budget
            WHERE id = :expense_id
        """)
        db.execute(update_query, {
            "title": title,
            "amount": amount,
            "dateinput": dateinput,
            "category": category,
            "budget": budget,
            "expense_id": expense_id
        })
        db.commit()

        return {
            "message": "Expense updated successfully",
            "data": {
                "title": title,
                "amount": amount,
                "dateinput": dateinput,
                "category": category,
                "budget": budget
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

# ------------------- RUN SERVER -------------------
if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("host", "127.0.0.1"), port=int(os.getenv("port", 8000)))