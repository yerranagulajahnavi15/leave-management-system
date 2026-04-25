# Employee Leave Management System
A full-stack web application built with Python Flask and MySQL.

## Tech Stack
- **Backend:** Python, Flask
- **Database:** MySQL
- **Frontend:** HTML, CSS, Bootstrap 5, Jinja2

## Setup Instructions

### Step 1 – Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 2 – Setup MySQL Database
- Open MySQL Workbench
- Run the entire `database.sql` file
- This creates the database and sample data

### Step 3 – Configure app.py
Open `app.py` and update these lines with your MySQL credentials:
```python
app.config['MYSQL_USER'] = 'root'       # your MySQL username
app.config['MYSQL_PASSWORD'] = ''       # your MySQL password
```

### Step 4 – Run the app
```bash
python app.py
```
Open browser at: http://127.0.0.1:5000

## Usage
1. Go to /register and create a Manager account
2. Go to /register again and create an Employee account
3. Login as Employee → Apply for leave
4. Login as Manager → Approve or Reject requests

## Features
- Role-based access (Employee & Manager)
- Leave balance tracking (20 days/year)
- Apply, approve, reject with comments
- Leave history with status badges
- Responsive Bootstrap UI
