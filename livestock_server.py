from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
import sqlite3
import datetime
import os
import hashlib

app = Flask(__name__)
app.secret_key = ' حيواني_secure_enterprise_2026'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# بيانات الاعتماد السيادية الموحدة
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("123456".encode()).hexdigest()

MAURITANIA_WILAYAS = [
    "نواكشوط الغربية", "نواكشوط الشمالية", "نواكشوط الجنوبية",
    "الحوض الشرقي - النعمة", "الحوض الغربي - عيون العتروس",
    "العصابة - كيفة", "كوركول - كيهيدي", "البراكنة - ألاك",
    "اترارزة - روصو", "إنشيري - آكجوجت", "داخلة نواذيبو",
    "تكانت - تجكجة", "كيدي ماغا - سيلبابي", "تيرس زمور - ازويرات", "آدارار - أطار"
]

def init_db():
    conn = sqlite3.connect('livestock_enterprise.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_number TEXT UNIQUE,
            animal_type TEXT,
            owner_username TEXT,
            health_status TEXT,
            temperature REAL,
            lat REAL,
            lng REAL,
            status TEXT,
            animal_photo TEXT,
            battery_level INTEGER DEFAULT 100,
            last_update TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feed_market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wilaya TEXT,
            feed_type TEXT,
            price_per_bag REAL,
            trend TEXT,
            updated_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetry_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_number TEXT,
            temperature REAL,
            lat REAL,
            lng REAL,
            log_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

SETTINGS = {
    "system_name": "نظام حيواني / المنصة السيادية لتتبع القطيع",
    "logo_url": "https://upload.wikimedia.org/wikipedia/commons/4/43/Flag_of_Mauritania.svg"
}

BASE_LAYOUT = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ system_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root { --dark-bg: #0b0b0b; --card-bg: #161616; --accent-gold: #ffc107; }
        body { background-color: var(--dark-bg); color: #f1f1f1; font-family: 'Segoe UI', Tahoma, sans-serif; }
        .sidebar { background: #111; min-height: 100vh; color: white; border-left: 4px solid var(--accent-gold); }
        .card-custom { border-radius: 14px; border: 1px solid #282828; background: var(--card-bg); color: #fff; margin-bottom: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.7); }
        .btn-warning { background-color: var(--accent-gold); border-color: var(--accent-gold); font-weight: bold; }
        .logo-img { width: 85px; height: 55px; object-fit: cover; border-radius: 8px; border: 2px solid var(--accent-gold); }
        .animal-thumb { width: 55px; height: 55px; object-fit: cover; border-radius: 10px; border: 2px solid var(--accent-gold); cursor: pointer; }
        .table { color: #fff; }
        .table-dark { background-color: #1f1f1f; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-lg-2 d-none d-lg-block sidebar p-3">
                <div class="text-center py-3">
                    <img src="{{ logo_url }}" class="logo-img mb-2" alt="علم موريتانيا">
                    <h6 class="text-warning fw-bold">نظام حيواني</h6>
                </div>
                <hr class="border-secondary">
                <nav class="nav nav-pills flex-column">
                    <a href="/admin-dashboard" class="nav-link text-white mb-2"><i class="fa-solid fa-chart-line me-2"></i> لوحة الإدارة</a>
                    <a href="/admin-animals" class="nav-link text-white mb-2"><i class="fa-solid fa-microchip me-2"></i> إدارة الشرائح</a>
                    <a href="/admin-market" class="nav-link text-white mb-2"><i class="fa-solid fa-store me-2"></i> بورصة الأعلاف</a>
                    <a href="/simulator" class="nav-link text-warning mb-2"><i class="fa-solid fa-satellite-dish me-2"></i> محاكي الإشارات</a>
                </nav>
                <div class="mt-4 pt-3 border-top border-secondary">
                    <a href="/client-dashboard" class="btn btn-warning w-100 btn-sm mb-2 text-dark">واجهة الزبائن ⚡</a>
                    <a href="/logout" class="btn btn-outline-danger w-100 btn-sm">خروج</a>
                </div>
            </div>
            <div class="col-lg-10 col-md-12 p-3 p-md-4">
                {% block content %}{% endblock %}
            </div>
        </div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

CLIENT_DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>واجهة الزبائن - نظام حيواني</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background: #0b0b0b; color: #f1f1f1; font-family: 'Segoe UI', Tahoma, sans-serif; }
        .card-custom { background: #161616; border: 1px solid #282828; border-radius: 14px; box-shadow: 0 6px 20px rgba(0,0,0,0.7); }
        .animal-thumb { width: 50px; height: 50px; object-fit: cover; border-radius: 8px; border: 2px solid #ffc107; cursor: pointer; }
        #client-map { height: 380px; border-radius: 12px; width: 100%; }
        .cam-box { background: #000; color: #0f0; border-radius: 10px; padding: 15px; text-align: center; font-family: monospace; }
        .table { color: #fff; }
        .table-dark { background-color: #1f1f1f; }
        .logo-header { width: 70px; height: 45px; object-fit: cover; border-radius: 6px; border: 2px solid #ffc107; }
    </style>
</head>
<body>
    <div class="container py-3">
        <div class="d-flex flex-column flex-md-row justify-content-between align-items-center mb-4 bg-dark text-white p-3 rounded shadow border border-secondary gap-3">
            <div class="d-flex align-items-center gap-3 text-center text-md-start">
                <img src="{{ logo_url }}" class="logo-header" alt="علم موريتانيا">
                <div>
                    <h4 class="text-warning fw-bold m-0 fs-5"><i class="fa-solid fa-satellite-dish me-2"></i> نظام حيواني (موريتانيا / اسطنبول)</h4>
                    <p class="text-muted small m-0">منصة تتبع الطوق، الكاميرا الحية، والبيانات الضخمة</p>
                </div>
            </div>
            <div class="d-flex gap-2 w-100 w-md-auto justify-content-center">
                <a href="/client-dashboard" class="btn btn-outline-warning btn-sm fw-bold">رابط الزبائن 🌐</a>
                <a href="/admin-login" class="btn btn-warning btn-sm fw-bold text-dark">رابط الإدارة 🔒</a>
            </div>
        </div>

        <div class="row g-4">
            <div class="col-12">
                <div class="card card-custom p-3 p-md-4">
                    <h5 class="fw-bold mb-3 text-warning"><i class="fa-solid fa-cow me-2"></i> أجهزة القطيع والشرائح النشطة (اضغط على الصورة لسماع صوت الحنين 🐪)</h5>
                    <div class="table-responsive">
                        <table class="table table-hover align-middle">
                            <thead class="table-dark">
                                <tr>
                                    <th>الصورة (الصوت)</th>
                                    <th>الشريحة (Tag)</th>
                                    <th>النوع</th>
                                    <th>الحرارة</th>
                                    <th>الحالة الصحية</th>
                                    <th>البطارية</th>
                                    <th>الكاميرا الحية (ESP32-CAM)</th>
                                    <th>المرعى</th>
                                    <th>إجراء طارئ</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for a in animals %}
                                <tr>
                                    <td>
                                        <img src="{{ url_for('static', filename='uploads/' + a[9]) }}" class="animal-thumb" onclick="playCamelSound()" title="صوت الحنين">
                                        <audio id="camelAudio" src="https://www.myinstants.com/media/sounds/camel-grunt.mp3"></audio>
                                    </td>
                                    <td class="fw-bold text-warning">#{{ a[1] }}</td>
                                    <td>{{ a[2] }}</td>
                                    <td class="fw-bold {% if a[5] > 39 %}text-danger{% else %}text-success{% endif %}">{{ a[5] }} °C</td>
                                    <td><span class="badge {% if 'سليم' in a[4] %}bg-success{% else %}bg-danger{% endif %}">{{ a[4] }}</span></td>
                                    <td><span class="badge bg-success"><i class="fa-solid fa-solar-panel me-1"></i> 99%</span></td>
                                    <td>
                                        <button class="btn btn-sm btn-dark text-warning border border-warning fw-bold" data-bs-toggle="modal" data-bs-target="#camModal{{ a[0] }}">
                                            <i class="fa-solid fa-video me-1"></i> فتح الكاميرا 🔴
                                        </button>
                                        <div class="modal fade" id="camModal{{ a[0] }}" tabindex="-1">
                                          <div class="modal-dialog modal-dialog-centered">
                                            <div class="modal-content bg-dark text-white border border-warning">
                                              <div class="modal-header border-secondary">
                                                <h5 class="modal-title text-warning">🔴 البث الحي للطوق - #{{ a[1] }}</h5>
                                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                                              </div>
                                              <div class="modal-body text-center">
                                                <div class="cam-box p-3 border border-success mb-3">
                                                    <img id="liveCamFeed" src="/api/get_image" alt="البث الحي للمزرعة" class="img-fluid rounded border border-warning" style="max-height: 300px;" onerror="this.onerror=null; this.src='https://via.placeholder.com/320x240?text=No+Live+Feed+Yet';">
                                                    <p class="text-warning small mt-2">تحديث تلقائي كل ثوانٍ لعرض حركة الكاميرا الحية</p>
                                                </div>
                                              </div>
                                            </div>
                                          </div>
                                        </div>
                                    </td>
                                    <td><span class="badge {% if 'مفقود' in a[8] %}bg-danger{% else %}bg-info text-dark{% endif %}">{{ a[8] }}</span></td>
                                    <td>
                                        <form action="/client-report-missing/{{ a[0] }}" method="POST">
                                            <button type="submit" class="btn btn-sm {% if 'مفقود' in a[8] %}btn-success{% else %}btn-outline-danger{% endif %}">
                                                {% if 'مفقود' in a[8] %}إلغاء{% else %}🚨 إبلاغ{% endif %}
                                            </button>
                                        </form>
                                    </td>
                                </tr>
                                {% endfor %}
                                {% if not animals %}
                                <tr><td colspan="9" class="text-center text-muted py-4">لا توجد أجهزة مسجلة حالياً.</td></tr>
                                {% endif %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="col-lg-6">
                <div class="card card-custom p-3 p-md-4">
                    <h5 class="fw-bold mb-3 text-warning"><i class="fa-solid fa-map-location-dot me-2"></i> خريطة التتبع الحية (GPS)</h5>
                    <div id="client-map"></div>
                </div>
            </div>
            <div class="col-lg-6">
                <div class="card card-custom p-3 p-md-4">
                    <h5 class="fw-bold mb-3 text-warning"><i class="fa-solid fa-store me-2"></i> بورصة أسعار الأعلاف (الولايات الـ 15)</h5>
                    <div class="table-responsive" style="max-height: 380px; overflow-y: auto;">
                        <table class="table table-sm table-striped align-middle">
                            <thead class="table-dark">
                                <tr><th>الولاية</th><th>نوع العلف</th><th>السعر</th><th>المؤشر</th></tr>
                            </thead>
                            <tbody>
                                {% for m in market_prices %}
                                <tr>
                                    <td class="fw-bold text-warning">{{ m[1] }}</td>
                                    <td>{{ m[2] }}</td>
                                    <td class="fw-bold text-white">{{ m[3] }} MRU</td>
                                    <td><span class="badge {% if 'منخفض' in m[4] %}bg-success{% else %}bg-danger{% endif %}">{{ m[4] }}</span></td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        function playCamelSound() { document.getElementById("camelAudio").play(); }
        var map = L.map('client-map').setView([18.0735, -15.9582], 6);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
        {% for a in animals %}
            {% if a[6] and a[7] %}
                L.marker([{{ a[6] }}, {{ a[7] }}]).addTo(map).bindPopup('<b>#{{ a[1] }}</b><br>الحرارة: {{ a[5] }}°C');
            {% endif %}
        {% endfor %}

        // تحديث صورة الكاميرا تلقائياً كل 3 ثوانٍ لتعطاء إيحاء البث الحي المتجدد
        setInterval(function() {
            var img = document.getElementById('liveCamFeed');
            if (img) {
                img.src = '/api/get_image?t=' + new Date().getTime();
            }
        }, 3000);
    </script>
</body>
</html>
'''

ADMIN_LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>دخول الإدارة - نظام حيواني</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #0b0b0b; color: white; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        .login-card { background: #161616; border: 2px solid #ffc107; border-radius: 16px; padding: 30px; width: 100%; max-width: 400px; text-align: center; }
        .login-logo { width: 90px; height: 60px; object-fit: cover; border-radius: 8px; border: 2px solid #ffc107; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="login-card shadow">
        <img src="{{ logo_url }}" class="login-logo" alt="علم موريتانيا">
        <h4 class="text-warning mb-1 fw-bold">نظام حيواني</h4>
        <p class="text-muted small mb-4">بوابة الإدارة المركزية المشفرة</p>
        {% if error %}<div class="alert alert-danger py-2 mb-3">{{ error }}</div>{% endif %}
        <form action="/admin-login" method="POST" class="text-start">
            <div class="mb-3">
                <label class="form-label text-warning small">اسم المستخدم (admin):</label>
                <input type="text" name="username" class="form-control bg-dark text-white border-secondary" value="admin" required>
            </div>
            <div class="mb-4">
                <label class="form-label text-warning small">كلمة المرور (123456):</label>
                <input type="password" name="password" class="form-control bg-dark text-white border-secondary" value="123456" required>
            </div>
            <button type="submit" class="btn btn-warning w-100 py-2 fw-bold text-dark shadow">تسجيل الدخول الإداري 🔒</button>
        </form>
        <div class="mt-3">
            <a href="/client-dashboard" class="text-success small text-decoration-none">← العودة لواجهة الزبائن</a>
        </div>
    </div>
</body>
</html>
'''

SIMULATOR_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>محاكي الإشارات</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-dark text-white d-flex align-items-center justify-content: center" style="min-height: 100vh;">
    <div class="container" style="max-width: 450px;">
        <div class="card bg-secondary border-warning p-4 shadow">
            <h4 class="text-warning fw-bold mb-3">📡 محاكاة إشارات ESP32 لقطيع حيواني</h4>
            {% if msg %}<div class="alert alert-success py-2">{{ msg }}</div>{% endif %}
            <form action="/simulator" method="POST">
                <div class="mb-3 text-start"><label class="form-label text-warning small">Tag ID:</label><input type="text" name="tag_number" class="form-control bg-dark text-white" value="TAG-MAURITANIA-01" required></div>
                <div class="mb-3 text-start"><label class="form-label text-warning small">درجة الحرارة (°C):</label><input type="number" step="any" name="temperature" class="form-control bg-dark text-white" value="38.6" required></div>
                <div class="row mb-3">
                    <div class="col-6 text-start"><label class="form-label text-warning small">Lat:</label><input type="number" step="any" name="lat" class="form-control bg-dark text-white" value="18.0735" required></div>
                    <div class="col-6 text-start"><label class="form-label text-warning small">Lng:</label><input type="number" step="any" name="lng" class="form-control bg-dark text-white" value="-15.9582" required></div>
                </div>
                <button type="submit" class="btn btn-warning w-100 fw-bold text-dark">🚀 إرسال البيانات للسيرفر</button>
            </form>
            <div class="mt-3 text-center"><a href="/client-dashboard" class="text-light small text-decoration-none">← العودة لواجهة الزبائن</a></div>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index(): return redirect(url_for('client_dashboard'))

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and hashlib.sha256(request.form['password'].encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            session['admin_logged'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template_string(ADMIN_LOGIN_HTML, error="بيانات غير صحيحة!", logo_url=SETTINGS["logo_url"])
    return render_template_string(ADMIN_LOGIN_HTML, logo_url=SETTINGS["logo_url"])

@app.route('/client-dashboard')
def client_dashboard():
    conn = sqlite3.connect('livestock_enterprise.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM animals')
    animals = cursor.fetchall()
    cursor.execute('SELECT * FROM feed_market')
    market_prices = cursor.fetchall()
    conn.close()
    return render_template_string(CLIENT_DASHBOARD_HTML, animals=animals, market_prices=market_prices, logo_url=SETTINGS["logo_url"])

@app.route('/client-report-missing/<int:animal_id>', methods=['POST'])
def client_report_missing(animal_id):
    conn = sqlite3.connect('livestock_enterprise.db')
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM animals WHERE id = ?', (animal_id,))
    res = cursor.fetchone()
    if res:
        new_status = 'آمن بالمرعى' if 'مفقود' in res[0] else '🚨 مفقود/مسروق'
        cursor.execute('UPDATE animals SET status = ? WHERE id = ?', (new_status, animal_id))
        conn.commit()
    conn.close()
    return redirect(url_for('client_dashboard'))

@app.route('/simulator', methods=['GET', 'POST'])
def simulator():
    msg = ""
    if request.method == 'POST':
        tag, temp, lat, lng = request.form['tag_number'], float(request.form['temperature']), float(request.form['lat']), float(request.form['lng'])
        health = "✅ سليم 100%" if temp <= 39.0 else "⚠️ اشتباه حمى"
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect('livestock_enterprise.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE animals SET temperature = ?, lat = ?, lng = ?, health_status = ?, last_update = ? WHERE tag_number = ?', (temp, lat, lng, health, now_str, tag))
        cursor.execute('INSERT INTO telemetry_logs (tag_number, temperature, lat, lng, log_time) VALUES (?, ?, ?, ?, ?)', (tag, temp, lat, lng, now_str))
        conn.commit()
        conn.close()
        msg = "✅ تم تحديث بيانات الشريحة بنجاح!"
    return render_template_string(SIMULATOR_HTML, msg=msg)


# --- 1. مسار استقبال بيانات الحساسات (درجة الحرارة) من ESP32 ---
@app.route('/api/sensor_update', methods=['POST'])
def receive_sensor_data():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400
        
    tag = data.get('tag_number', 'TAG-MAURITANIA-01')
    temperature = data.get('temperature', 38.5)
    
    health = "✅ سليم 100%" if float(temperature) <= 39.0 else "⚠️ اشتباه حمى"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect('livestock_enterprise.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE animals SET temperature = ?, health_status = ?, last_update = ? WHERE tag_number = ?', (temperature, health, now_str, tag))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "message": "Sensor data received!"}), 200


# --- 2. مسارات استقبال وعرض صور الكاميرا الحية من ESP32-CAM ---
UPLOAD_FOLDER_CAM = 'static/uploads'
os.makedirs(UPLOAD_FOLDER_CAM, exist_ok=True)
latest_image_path = os.path.join(UPLOAD_FOLDER_CAM, 'latest_livestock.jpg')

@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    if request.data:
        with open(latest_image_path, 'wb') as f:
            f.write(request.data)
        return jsonify({"status": "success"}), 200
        
    if 'imageFile' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    file = request.files['imageFile']
    file.save(latest_image_path)
    return jsonify({"status": "success"}), 200

@app.route('/api/get_image', methods=['GET'])
def get_image():
    from flask import send_file
    if os.path.exists(latest_image_path):
        return send_file(latest_image_path, mimetype='image/jpeg')
    return "No image", 404


@app.route('/logout')
def logout(): session.pop('admin_logged', None); return redirect(url_for('admin_login'))

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    conn = sqlite3.connect('livestock_enterprise.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM animals')
    total = cursor.fetchone()[0]
    conn.close()
    content = f'''
    <h3 class="fw-bold mb-4 text-warning"><i class="fa-solid fa-chart-line me-2"></i> لوحة التحكم السيادية - نظام حيواني</h3>
    <div class="card card-custom p-4 text-center">
        <h4 class="text-success fw-bold">إجمالي الأجهزة والشرائح المرتبطة: {total}</h4>
        <div class="mt-3">
            <a href="/admin-animals" class="btn btn-success me-2 fw-bold">إدارة الشرائح والأجهزة</a>
            <a href="/admin-market" class="btn btn-warning text-dark me-2 fw-bold">بورصة الأعلاف</a>
            <a href="/client-dashboard" class="btn btn-dark border border-warning text-warning fw-bold">واجهة الزبائن</a>
        </div>
    </div>
    '''
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), system_name=SETTINGS["system_name"], logo_url=SETTINGS["logo_url"])

@app.route('/admin-animals', methods=['GET', 'POST'])
def admin_animals():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    if request.method == 'POST':
        photo = request.files.get('animal_photo')
        photo_name = "default_animal.jpg"
        if photo and photo.filename != '':
            photo_name = photo.filename
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_name))
        conn = sqlite3.connect('livestock_enterprise.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO animals (tag_number, animal_type, owner_username, health_status, temperature, lat, lng, status, animal_photo, last_update) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (request.form['tag_number'], request.form['animal_type'], request.form['owner_username'], '✅ سليم 100%', float(request.form['temp']), 18.0735, -15.9582, 'آمن بالمرعى', photo_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_animals'))
    conn = sqlite3.connect('livestock_enterprise.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM animals')
    animals = cursor.fetchall()
    conn.close()
    rows = ""
    for a in animals:
        rows += f'<tr><td><img src="{url_for("static", filename="uploads/" + a[9])}" class="animal-thumb"></td><td class="fw-bold text-warning">#{a[1]}</td><td>{a[2]}</td><td>{a[3]}</td><td>{a[5]} °C</td><td><a href="/delete_animal/{a[0]}" class="btn btn-sm btn-outline-danger"><i class="fa-solid fa-trash"></i></a></td></tr>'
    if not animals: rows = '<tr><td colspan="6" class="text-center text-muted">لا توجد أجهزة مسجلة.</td></tr>'
    content = f'''
    <h3 class="fw-bold mb-4 text-warning"><i class="fa-solid fa-microchip me-2"></i> إدارة الشرائح والأجهزة</h3>
    <div class="card card-custom p-4 mb-4">
        <form action="/admin-animals" method="POST" enctype="multipart/form-data" class="row g-3">
            <div class="col-md-3"><input type="text" name="tag_number" class="form-control bg-dark text-white border-secondary" placeholder="Tag ID" required></div>
            <div class="col-md-3"><input type="text" name="animal_type" class="form-control bg-dark text-white border-secondary" placeholder="النوع (ناقة، شاة)" required></div>
            <div class="col-md-3"><input type="text" name="owner_username" class="form-control bg-dark text-white border-secondary" placeholder="اسم المربي" required></div>
            <div class="col-md-3"><input type="number" step="any" name="temp" class="form-control bg-dark text-white border-secondary" value="38.5" required></div>
            <div class="col-md-6"><input type="file" name="animal_photo" class="form-control bg-dark text-white border-secondary" accept="image/*" required></div>
            <div class="col-md-6"><button type="submit" class="btn btn-warning w-100 fw-bold text-dark">حفظ وتفعيل الشريحة 🚀</button></div>
        </form>
    </div>
    <div class="card card-custom p-4"><div class="table-responsive"><table class="table table-hover align-middle"><thead class="table-dark"><tr><th>الصورة</th><th>Tag</th><th>النوع</th><th>المربي</th><th>الحرارة</th><th>إجراء</th></tr></thead><tbody>{rows}</tbody></table></div></div>
    '''
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), system_name=SETTINGS["system_name"], logo_url=SETTINGS["logo_url"])

@app.route('/delete_animal/<int:id>')
def delete_animal(id):
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    conn = sqlite3.connect('livestock_enterprise.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM animals WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_animals'))

@app.route('/admin-market', methods=['GET', 'POST'])
def admin_market():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    if request.method == 'POST':
        conn = sqlite3.connect('livestock_enterprise.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO feed_market (wilaya, feed_type, price_per_bag, trend, updated_date) VALUES (?, ?, ?, ?, ?)',
                       (request.form['wilaya'], request.form['feed_type'], float(request.form['price']), request.form['trend'], datetime.datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_market'))
    conn = sqlite3.connect('livestock_enterprise.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM feed_market')
    market = cursor.fetchall()
    conn.close()
    opts = "".join([f'<option value="{w}">{w}</option>' for w in MAURITANIA_WILAYAS])
    rows = "".join([f'<tr><td class="fw-bold text-warning">{m[1]}</td><td>{m[2]}</td><td>{m[3]} MRU</td><td><a href="/delete_market/{m[0]}" class="btn btn-sm btn-outline-danger"><i class="fa-solid fa-trash"></i></a></td></tr>' for m in market])
    if not market: rows = '<tr><td colspan="4" class="text-center text-muted">لا توجد أسعار مسجلة.</td></tr>'
    content = f'''
    <h3 class="fw-bold mb-4 text-warning"><i class="fa-solid fa-store me-2"></i> بورصة أسعار الأعلاف (15 ولاية)</h3>
    <div class="card card-custom p-4 mb-4">
        <form action="/admin-market" method="POST" class="row g-3">
            <div class="col-md-3"><select name="wilaya" class="form-select bg-dark text-white border-secondary" required><option value="">اختر الولاية...</option>{opts}</select></div>
            <div class="col-md-3"><input type="text" name="feed_type" class="form-control bg-dark text-white border-secondary" placeholder="نوع العلف" required></div>
            <div class="col-md-3"><input type="number" step="any" name="price" class="form-control bg-dark text-white border-secondary" placeholder="السعر (MRU)" required></div>
            <div class="col-md-3"><button type="submit" class="btn btn-warning w-100 fw-bold text-dark">حفظ السعر 📊</button></div>
        </form>
    </div>
    <div class="card card-custom p-4"><div class="table-responsive"><table class="table table-hover align-middle"><thead class="table-dark"><tr><th>الولاية</th><th>العلف</th><th>السعر</th><th>إجراء</th></tr></thead><tbody>{rows}</tbody></table></div></div>
    '''
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), system_name=SETTINGS["system_name"], logo_url=SETTINGS["logo_url"])

@app.route('/delete_market/<int:id>')
def delete_market(id):
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    conn = sqlite3.connect('livestock_enterprise.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM feed_market WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_market'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
