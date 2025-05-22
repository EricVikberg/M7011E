# M7011E

# E-commerce API

## Project Overview
A Django REST Framework-based e-commerce API with:
- User authentication (Tokens)
- Product & category management  
- Shopping cart functionality
- Order processing system
- Role-based permissions (Customer, Staff, Admin)

## Setup Instructions

### Prerequisites
- Python 3.8+
- pip
- SQLite (included with Python)

### Installation
```bash```
git clone <repository-url>
cd ecommerce

# Create virtual environment
python -m venv .env
source .env/bin/activate  
# Windows: .env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

## Database

The project includes a pre-configured SQLite database (`db.sqlite3`) containing:

## Running the Server

Start the development server with:

```bash```
python manage.py runserver

## Access Points

The API will be available at:  
[http://localhost:8000/](http://localhost:8000/)

For full API documentation with interactive endpoints, visit:  
[http://localhost:8000/swagger/](http://localhost:8000/swagger/)
