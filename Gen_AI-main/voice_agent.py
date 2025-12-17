import google.generativeai as genai
import sqlite3
from datetime import datetime
from gtts import gTTS
from io import BytesIO

class VoiceAgent:
    def __init__(self, api_key):
        """Inisialisasi Agen Suara dengan API Key Gemini"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def _get_financial_data(self, db_path):
        """Mengambil ringkasan data keuangan dari database"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Ambil data mulai tanggal 1 bulan ini
            now = datetime.now()
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            cursor.execute('''
                SELECT r.amount, c.main_category, c.name 
                FROM records r
                JOIN categories c ON r.category_id = c.id
                WHERE r.timestamp >= ?
            ''', (start_date.strftime('%Y-%m-%d %H:%M:%S'),))
            
            data = cursor.fetchall()
            conn.close()

            income = sum(x[0] for x in data if x[1] == 'income')
            expense = sum(x[0] for x in data if x[1] == 'expense')
            balance = income - expense
            
            # Cari pengeluaran terbesar
            expenses_only = [x for x in data if x[1] == 'expense']
            top_category = "belum ada"
            if expenses_only:
                cat_totals = {}
                for amt, _, name in expenses_only:
                    cat_totals[name] = cat_totals.get(name, 0) + amt
                top_category = max(cat_totals, key=cat_totals.get)
            
            return {
                "income": income,
                "expense": expense,
                "balance": balance,
                "top_category": top_category
            }
        except Exception as e:
            print(f"Error reading DB: {e}")
            return None

    def _generate_script(self, data):
        """Meminta Gemini membuat naskah spoken word"""
        if not data:
            return "Maaf, saya tidak bisa mengakses data keuangan saat ini."

        try:
            prompt = f"""
            Buatkan naskah singkat (maksimal 400 karakter) untuk diucapkan oleh asisten keuangan pribadi.
            Gaya bahasa: Santai, akrab, suportif, bahasa Indonesia gaul tapi sopan.
            JANGAN gunakan simbol markdown (seperti bintang * atau pagar #) karena ini untuk suara.
            
            Data Keuangan User Bulan Ini:
            - Pemasukan: Rp {data['income']:,.0f}
            - Pengeluaran: Rp {data['expense']:,.0f}
            - Sisa Uang: Rp {data['balance']:,.0f}
            - Kategori paling boros: {data['top_category']}
            
            Struktur naskah:
            1. Sapa user dengan ramah.
            2. Bacakan kondisi keuangannya (sehat/kritis) berdasarkan sisa uang.
            3. Sentil sedikit soal kategori paling boros (jika ada).
            4. Tutup dengan semangat.
            """
            
            response = self.model.generate_content(prompt)
            # Bersihkan markdown agar tidak terbaca oleh TTS
            return response.text.replace("*", "").replace("#", "")
        except Exception as e:
            return "Halo! Maaf, sistem otak saya sedang gangguan, jadi belum bisa kasih analisis lengkap."

    def create_voice_analysis(self, db_path):
        """Fungsi utama: Ambil data -> Buat Naskah -> Jadi Suara"""
        # 1. Ambil Data
        data = self._get_financial_data(db_path)
        
        # 2. Buat Naskah
        script_text = self._generate_script(data)
        
        # 3. Konversi ke Suara
        try:
            tts = gTTS(text=script_text, lang='id', slow=False)
            voice_buf = BytesIO()
            tts.write_to_fp(voice_buf)
            voice_buf.seek(0)
            return voice_buf, script_text
        except Exception as e:
            print(f"TTS Error: {e}")
            return None, f"Gagal membuat suara: {e}"