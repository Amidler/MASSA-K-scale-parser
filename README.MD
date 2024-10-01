# Scale Data Parser

This project is a Python application for parsing weight data from scales MASSA-K (https://massa.ru), storing the data in a MySQL database, and scheduling periodic data collection. The project uses UDP/TCP to communicate with the scale, processes the received data, and inserts it into the database.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)

## Installation

### Step 1: Clone the repository

First, clone this repository to your local machine:

```bash
git clone https://github.com/your_username/MASSA-K-scale-parser.git
cd MASSA-K-scale-parser

### Step 2: Adjust connections 
Adjust config section in file gluescales_lamiflex.py like this:

ip = "192.168.1.200"
port = 5001 

config = {
    'user': 'username_mysql',
    'password': 'password_mysql',
    'host': 'host with SQL server',
    'database': 'database for table',
}

### Step 3: Setup virual enviroment

python3 -m venv venv
source venv/bin/activate

### Step 4: Install dependencies

pip install -r requirements.txt

## Usage

Just run .sh file
./gluescales.sh