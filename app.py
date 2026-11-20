import streamlit as st
import pandas as pd
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from collections import Counter
import re
import io
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="Akademik YouTube Veri Madenciliği", page_icon="📊", layout="wide")

# --- 1. ERİŞİM ŞİFRESİ KORUMASI ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Akademik Veri & Metin Madenciliği Portalı")
    st.markdown("Bu araç nitel ve karma yöntem araştırmaları için özel olarak geliştirilmiştir.")
    password = st.text_input("Erişim Şifresini Giriniz:", type="password")
    if st.button("Giriş Yap"):
        if password == "IHU2026":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Hatalı erişim şifresi! Lütfen yetkili ile iletişime geçin.")
    st.stop()

# --- YARDIMCI FONKSİYONLAR ---
STOP_WORDS = {
    "ve", "ile", "bir", "bu", "ama", "için", "de", "da", "ne", "o", "çok", "daha",
    "gibi", "kadar", "olarak", "var", "yok", "mi", "mı", "mu", "mü", "ben", "sen",
    "biz", "siz", "onlar", "şu", "her", "şey", "bi", "yani", "işte", "mesela", "aslında",
    "zaten", "fakat", "lakin", "ancak", "veya", "ya", "hem", "ki", "en", "diğer", "sonra",
    "önce", "şimdi", "böyle", "şöyle", "nasıl", "neden", "niçin", "kim", "hangi", "the",
    "and", "to", "of", "in", "is", "it", "you", "that", "for", "on", "are", "with", "as"
}

def extract_video_id(url):
    parsed = urlparse(url.strip())
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        return parsed.path[1:]
    if parsed.hostname in ("youtube.com", "://youtube.com", "://youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith(("/embed/", "/v/", "/shorts/")):
            return parsed.path.split("/")[2]
    return None

def get_keywords(text, top_n=5):
    if not text or text == "Altyazı Bulunamadı":
        return "-"
    words = re.findall(r'\b[a-zçğıöşüA-ZÇĞIİÖŞÜ]{3,}\b', text.lower())
    filtered = [w for w in words if w not in STOP_WORDS]
    most_common = Counter(filtered).most_common(top_n)
    return ", ".join([f"{word} ({count})" for word, count in most_common])

def fetch_transcript(video_id):
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(['tr', 'en'])
        except Exception:
            transcript = next(iter(transcript_list))
        fetched = transcript.fetch()
        full_text = " ".join([snippet.text for snippet in fetched])
        return re.sub(r'\s+', ' ', full_text).strip()
    except Exception:
        return "Altyazı Bulunamadı"

# --- ANA UYGULAMA ARAYÜZÜ ---
st.title("📊 Akademik YouTube Veri & Transkript Toplama Aracı")
st.markdown("MAXQDA, NVivo ve SPSS analizleri için temizlenmiş, yapılandırılmış veri seti üretici.")

urls_input = st.text_area(
    "YouTube Video Linklerini Alt Alta Yapıştırın (Tek seferde en fazla 10 link):",
    height=150,
    placeholder="https://://youtube.com/watch?v=...\nhttps://youtu.be..."
)

if st.button("🚀 Verileri Çek ve Analiz Et", type="primary"):
    raw_urls = [u.strip() for u in urls_input.splitlines() if u.strip()]
    
    if not raw_urls:
        st.warning("Lütfen en az bir geçerli YouTube linki girin.")
    elif len(raw_urls) > 10:
        st.error("Lütfen tek seferde en fazla 10 video linki girin.")
    else:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
        
        for idx, url in enumerate(raw_urls):
            status_text.text(f"İşleniyor ({idx + 1}/{len(raw_urls)}): {url}")
            video_id = extract_video_id(url)
            
            if not video_id:
                results.append({
                    "Video Linki": url, "Başlık": "Geçersiz Link", "Kanal": "-",
                    "Yayın Tarihi": "-", "İzlenme": 0, "Beğeni": 0,
                    "Kelime Sayısı": 0, "En Sık Geçen 5 Anahtar Kelime": "-", "Transkript (Metin)": "-"
                })
                progress_bar.progress((idx + 1) / len(raw_urls))
                continue

            # Meta verileri çek
            title, channel, pub_date, views, likes = "Bilinmiyor", "Bilinmiyor", "-", 0, 0
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get("title", "Bilinmiyor")
                    channel = info.get("uploader", "Bilinmiyor")
                    raw_date = info.get("upload_date", "")
                    if len(raw_date) == 8:
                        pub_date = f"{raw_date[6:8]}.{raw_date[4:6]}.{raw_date[0:4]}"
                    views = info.get("view_count", 0) or 0
                    likes = info.get("like_count", 0) or 0
            except Exception:
                pass

            # Altyazı çek ve analiz et
            transcript_text = fetch_transcript(video_id)
            word_count = len(transcript_text.split()) if transcript_text != "Altyazı Bulunamadı" else 0
            keywords = get_keywords(transcript_text, top_n=5)

            results.append({
                "Video Linki": url,
                "Başlık": title,
                "Kanal": channel,
                "Yayın Tarihi": pub_date,
                "İzlenme": views,
                "Beğeni": likes,
                "Kelime Sayısı": word_count,
                "En Sık Geçen 5 Anahtar Kelime": keywords,
                "Transkript (Metin)": transcript_text
            })
            progress_bar.progress((idx + 1) / len(raw_urls))

        status_text.success("✅ Tüm videolar başarıyla işlendi!")
        df = pd.DataFrame(results)

        # Özet Metrik Kartları
        col1, col2, col3 = st.columns(3)
        col1.metric("İşlenen Video Sayısı", len(df))
        col2.metric("Toplam Çekilen Kelime", f"{df['Kelime Sayısı'].sum():,}")
        col3.metric("Toplam İzlenme", f"{df['İzlenme'].sum():,}")

        st.subheader("📋 Veri Önizleme (MAXQDA Formatı)")
        st.dataframe(df, use_container_width=True)

        # Excel İndirme Butonu
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='MAXQDA_Veri_Seti')
        
        st.download_button(
            label="📥 MAXQDA Uyumlu Excel (.xlsx) İndir",
            data=output.getvalue(),
            file_name="akademik_youtube_veri_seti.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
