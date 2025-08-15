from flask import Flask, render_template, request, jsonify
import sqlite3
import datetime
import locale # <-- Import modul locale

app = Flask(__name__)

# Coba set locale ke Indonesia, tangani error jika tidak ada
try:
    locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Indonesian_Indonesia.1252')
    except locale.Error:
        print("Peringatan: Locale 'id_ID' atau 'Indonesian' tidak ditemukan. Format tanggal mungkin dalam Bahasa Inggris.")


def get_db_connection():
    # ... (fungsi ini tidak berubah)
    conn = sqlite3.connect('database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def dashboard():
    conn = get_db_connection()
    today = datetime.date.today()
    
    # Ambil nama bulan
    nama_bulan_ini = today.strftime('%B %Y')

    # --- (Sisa logika untuk mengambil data lainnya tidak berubah) ---
    hari_ini_data = conn.execute('SELECT SUM(jumlah) as total_jumlah, SUM(total_penjualan) as total_rupiah FROM penjualan WHERE tanggal = ?', (today.strftime('%Y-%m-%d'),)).fetchone()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    minggu_ini_data = conn.execute('SELECT SUM(jumlah) as total_jumlah, SUM(total_penjualan) as total_rupiah FROM penjualan WHERE tanggal >= ?', (start_of_week.strftime('%Y-%m-%d'),)).fetchone()
    start_of_month = today.replace(day=1)
    bulan_ini_data = conn.execute('SELECT SUM(jumlah) as total_jumlah, SUM(total_penjualan) as total_rupiah FROM penjualan WHERE tanggal >= ?', (start_of_month.strftime('%Y-%m-%d'),)).fetchone()
    histori = conn.execute('SELECT * FROM penjualan ORDER BY id DESC').fetchall()
    labels_harian, data_harian = [], []
    tanggal_mulai_harian = today - datetime.timedelta(days=6)
    for i in range(7):
        current_date = tanggal_mulai_harian + datetime.timedelta(days=i)
        labels_harian.append(current_date.strftime('%a, %d %b'))
        data_harian.append(0)
    results_harian = conn.execute('SELECT tanggal, SUM(jumlah) as total_jumlah FROM penjualan WHERE tanggal >= ? GROUP BY tanggal', (tanggal_mulai_harian.strftime('%Y-%m-%d'),)).fetchall()
    for row in results_harian:
        tanggal_db = datetime.datetime.strptime(row['tanggal'], '%Y-%m-%d').date()
        if tanggal_mulai_harian <= tanggal_db <= today:
            index = (tanggal_db - tanggal_mulai_harian).days
            data_harian[index] = row['total_jumlah']
    labels_mingguan = ['Minggu ke-1', 'Minggu ke-2', 'Minggu ke-3', 'Minggu ke-4']
    data_mingguan = [0, 0, 0, 0]
    results_bulanan = conn.execute('SELECT tanggal, jumlah FROM penjualan WHERE strftime("%Y-%m", tanggal) = ?', (today.strftime('%Y-%m'),)).fetchall()
    for row in results_bulanan:
        tanggal_db = datetime.datetime.strptime(row['tanggal'], '%Y-%m-%d').date()
        hari_ke = tanggal_db.day
        if 1 <= hari_ke <= 7: data_mingguan[0] += row['jumlah']
        elif 8 <= hari_ke <= 14: data_mingguan[1] += row['jumlah']
        elif 15 <= hari_ke <= 21: data_mingguan[2] += row['jumlah']
        elif 22 <= hari_ke <= 31: data_mingguan[3] += row['jumlah']

    conn.close()

    return render_template(
        'dashboard.html',
        hari_ini=hari_ini_data,
        minggu_ini=minggu_ini_data,
        bulan_ini=bulan_ini_data,
        histori=histori,
        harga=300,
        labels_harian=labels_harian,
        data_harian=data_harian,
        labels_mingguan=labels_mingguan,
        data_mingguan=data_mingguan,
        nama_bulan_ini=nama_bulan_ini # <-- Kirim nama bulan ke template
    )

@app.route('/info')
def info():
    return render_template('info.html')

@app.route('/kirim_data', methods=['POST'])
def kirim_data():
    try:
        # 1. Ambil data JSON yang dikirim dari Raspi
        data = request.get_json()
        jumlah_bibit = data['jumlah']
        
        # 2. Lakukan perhitungan
        harga_per_ekor = 300  # Asumsi harga
        total_penjualan = jumlah_bibit * harga_per_ekor
        tanggal_sekarang = datetime.date.today().strftime('%Y-%m-%d')
        
        # 3. Masukkan ke database
        conn = get_db_connection()
        conn.execute('INSERT INTO penjualan (tanggal, jumlah, total_penjualan) VALUES (?, ?, ?)',
                     (tanggal_sekarang, jumlah_bibit, total_penjualan))
        conn.commit()
        conn.close()
        
        print(f"SUKSES: Menerima {jumlah_bibit} ekor bibit dan sudah disimpan ke database.")
        
        # 4. [PENTING] Kirim balasan sukses ke Raspi
        return jsonify({'message': 'Data berhasil diterima'}), 200

    except Exception as e:
        print(f"ERROR di server: {e}")
        # 5. [PENTING] Kirim balasan error ke Raspi jika ada masalah
        return jsonify({'message': 'Terjadi error di server'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)