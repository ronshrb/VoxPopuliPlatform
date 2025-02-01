from flask import Flask, render_template, jsonify, send_file
import pandas as pd
import io
import matplotlib.pyplot as plt

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/users')
def users():
    return render_template('users.html')

@app.route('/database')
def database():
    # Read the Excel file
    df = pd.read_excel('output(3).xlsx')
    df['censored_content'] = df['censored_content'].fillna(df['content'])
    df = df[['date', 'time', 'censored_content']]
    # Convert the DataFrame to HTML
    table_html = df.to_html(classes='data-table', index=False)
    return render_template('database.html', table_html=table_html)

@app.route('/plot/users')
def plot_users():
    dates = ['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04', '2025-01-05']
    values = [10, 20, 30, 40, 50]

    plt.figure()
    plt.plot(dates, values, marker='o')
    plt.title('Number of Users by Date')
    plt.xlabel('Date')
    plt.ylabel('Number of Users')
    plt.grid(True)

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    return send_file(img, mimetype='image/png')

@app.route('/plot/chats')
def plot_chats():
    dates = ['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04', '2025-01-05']
    values = [5, 15, 25, 35, 45]

    plt.figure()
    plt.plot(dates, values, marker='o')
    plt.title('Number of Active Chats by Date')
    plt.xlabel('Date')
    plt.ylabel('Number of Active Chats')
    plt.grid(True)

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    return send_file(img, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)