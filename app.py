import streamlit as st
import pandas as pd
import yt_dlp
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from collections import Counter
import re
import io
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="Akademik Veri & İçgörü Stüdyosu", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .main-header {font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0;}
    .sub-header {font-size: 1.1rem; color: #4B5563; margin-bottom: 1.5rem;}
    .stMetric {background-color: #F8FAFC; padding: 15px; border-radius: 10px; border-left: 5px solid #2563EB;}
    </style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<p class="main-header">🎓 Akademik Veri & İçgörü Stüdyosu</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Nitel ve Karma Yöntem Araştırmaları İçin Otomatik Veri Madenciliği Platformu</p>', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])
    with col1:
        password = st.text_input("Araştırmacı Erişim Şifresi:", type="password", placeholder="Şifreyi giriniz...")
        if st.button("Sisteme Giriş Yap", type="primary"):
            if password == "IHU2026":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Hatalı şifre! Demo erişimi için geliştirici ile iletişime geçin.")
    st.stop()

STOP_WORDS = {
    "ve", "ile", "bir", "bu", "ama", "için", "de", "da", "ne", "o", "çok", "daha",
    "gibi", "kadar", "olarak", "var", "yok", "mi", "mı", "mu", "mü", "ben", "sen",
    "biz", "siz", "onlar", "şu", "her", "şey", "bi", "yani", "işte", "mesela", "aslında",
    "zaten", "fakat", "lakin", "ancak", "veya", "ya", "hem", "ki", "en", "diğer", "sonra",
    "önce", "şimdi", "böyle", "şöyle", "nasıl", "neden", "niçin", "kim", "hangi", "the",
    "and", "to", "of", "in", "is", "it", "you", "that", "for", "on", "are", "with", "as",
    "this", "was", "have", "be", "at", "or", "from", "by", "not", "but", "what", "all", "we"
}

def extract_video_id(url):
    parsed = urlparse(url.strip())
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        return parsed.path[1:]
    if parsed.hostname and "youtube.com" in parsed.hostname:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith(("/embed/", "/v/", "/shorts/")):
            return parsed.path.split("/")[2]
    return None

def get_keywords_dict(text, top_n=10):
    if not text or text.startswith("Altyazı"):
        return {}
    words = re.findall(r'\b[a-zçğıöşüA-ZÇĞIİÖŞÜ]{3,}\b', text.lower())
    filtered = [w for w in words if w not in STOP_WORDS]
    return dict(Counter(filtered).most_common(top_n))

def format_keywords(kw_dict, limit=5):
    if not kw_dict:
        return "-"
    items = list(kw_dict.items())[:limit]
    return ", ".join([f"{w} ({c})" for w, c in items])

def fetch_transcript_robust(video_id, info_dict):
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(['tr', 'en'])
        except Exception:
            transcript = next(iter(transcript_list))
        fetched = transcript.fetch()
        full_text = " ".join([snippet.text for snippet in fetched])
        cleaned = re.sub(r'\s+', ' ', full_text).strip()
        if len(cleaned) > 20:
            return cleaned, "Manuel/API Altyazı"
    except Exception:
        pass

    try:
        subs = info_dict.get("subtitles", {}) or {}
        auto_subs = info_dict.get("automatic_captions", {}) or {}
        target_sub = None
        for lang in ['tr', 'en']:
            if lang in subs:
                target_sub = subs[lang]
                break
            if lang in auto_subs:
                target_sub = auto_subs[lang]
                break
        if not target_sub and auto_subs:
            first_lang = next(iter(auto_subs))
            target_sub = auto_subs[first_lang]

        if target_sub:
            json3_url = next((item['url'] for item in target_sub if item.get('ext') == 'json3'), None)
            if json3_url:
                resp = requests.get(json3_url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    words = []
                    for event in data.get("events", []):
                        for seg in event.get("segs", []):
                            txt = seg.get("utf8", "").strip()
                            if txt and txt != "\n":
                                words.append(txt)
                    cleaned = re.sub(r'\s+', ' ', " ".join(words)).strip()
                    if len(cleaned) > 20:
                        return cleaned, "Otomatik Deşifre (AI)"
    except Exception:
        pass

    desc = (info_dict.get("description") or "").strip()
    if len(desc) > 30:
        return re.sub(r'\s+', ' ', desc), "Video Açıklaması (Yedek)"
    
    return "Altyazı Mevcut Değil", "Yok"

SAMPLE_URLS = "https://youtu.be\nhttps://youtu.be\nhttps://youtu.be"

st.markdown('<p class="main-header">🎓 Akademik Veri & İçgörü Stüdyosu</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">YouTube içeriklerinden saniyeler içinde MAXQDA, NVivo ve SPSS uyumlu yapılandırılmış veri seti ve içerik analizi üretin.</p>', unsafe_allow_html=True)

col_input1, col_input2 = st.columns([3, 1])
with col_input2:
    st.write("")
    st.write("")
    if st.button("✨ Örnek Linkleri Doldur"):
        st.session_state.url_box = SAMPLE_URLS
    fetch_comments = st.checkbox("💬 İzleyici Yorumlarını da Çek (İlk 15 yorum)", value=True)

with col_input1:
    urls_input = st.text_area(
        "Analiz Edilecek YouTube Video Linklerini Alt Alta Yapıştırın (Maksimum 10 link):",
        height=140,
        key="url_box",
        placeholder="https://youtu.be..."
    )
if st.button("🚀 Veri Madenciliğini Başlat ve Rapor Üret", type="primary", use_container_width=True):
    raw_urls = [u.strip() for u in urls_input.splitlines() if u.strip()]
    
    if not raw_urls:
        st.warning("Lütfen en az bir YouTube linki girin veya sağdaki 'Örnek Linkleri Doldur' butonuna basın.")
    elif len(raw_urls) > 10:
        st.error("Tek seferde maksimum 10 video işlenebilir.")
    else:
        results = []
        comments_data = []
        all_text_combined = ""
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'getcomments': fetch_comments,
            'extractor_args': {'youtube': {'max_comments': ['15', 'all', '0', '0']}} if fetch_comments else {}
        }
        
        for idx, url in enumerate(raw_urls):
            status_text.info(f"⏳ Veri çekiliyor ve işleniyor ({idx + 1}/{len(raw_urls)}): {url}")
            video_id = extract_video_id(url)
            
            if not video_id:
                progress_bar.progress((idx + 1) / len(raw_urls))
                continue

            title, channel, pub_date, views, likes, duration_min = "Bilinmiyor", "Bilinmiyor", "-", 0, 0, 0
            info = {}
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False) or {}
                    title = info.get("title", "Bilinmiyor")
                    channel = info.get("uploader", "Bilinmiyor")
                    raw_date = info.get("upload_date", "")
                    if len(raw_date) == 8:
                        pub_date = f"{raw_date[6:8]}.{raw_date[4:6]}.{raw_date[0:4]}"
                    views = info.get("view_count", 0) or 0
                    likes = info.get("like_count", 0) or 0
                    duration_min = round((info.get("duration", 0) or 0) / 60, 1)

                    if fetch_comments and info.get("comments"):
                        for c in info.get("comments", [])[:15]:
                            comments_data.append({
                                "Video Başlığı": title,
                                "Kanal": channel,
                                "Yorum Yazan": c.get("author", "Anonim"),
                                "Yorum Beğeni": c.get("like_count", 0) or 0,
                                "Yorum Metni": re.sub(r'\s+', ' ', c.get("text", "")).strip()
                            })
            except Exception:
                pass

            transcript_text, source_type = fetch_transcript_robust(video_id, info)
            word_count = len(transcript_text.split()) if source_type != "Yok" else 0
            kw_dict = get_keywords_dict(transcript_text, top_n=5)
            eng_rate = round((likes / views) * 100, 2) if views > 0 else 0.0

            if source_type != "Yok":
                all_text_combined += " " + transcript_text

            results.append({
                "Kanal": channel,
                "Video Başlığı": title,
                "Yayın Tarihi": pub_date,
                "Süre (Dk)": duration_min,
                "İzlenme": views,
                "Beğeni": likes,
                "Etkileşim (%)": eng_rate,
                "Veri Kaynağı": source_type,
                "Kelime Sayısı": word_count,
                "Baskın Kavramlar (Top 5)": format_keywords(kw_dict, 5),
                "Transkript / Metin": transcript_text,
                "Video Linki": url
            })
            progress_bar.progress((idx + 1) / len(raw_urls))

        status_text.success("✅ Analiz Tamamlandı! Veri seti MAXQDA ve Excel aktarımı için hazır.")
        df = pd.DataFrame(results)
        df_comments = pd.DataFrame(comments_data)

        st.divider()
        st.subheader("📊 Araştırma Veri Seti Özeti")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Analiz Edilen Video", f"{len(df)} Adet")
        c2.metric("Toplam Deşifre Kelime", f"{df['Kelime Sayısı'].sum():,}")
        c3.metric("Çekilen İzleyici Yorumu", f"{len(df_comments)} Adet")
        c4.metric("Ort. Etkileşim Oranı", f"%{df['Etkileşim (%)'].mean():.2f}")

        global_kw = get_keywords_dict(all_text_combined, top_n=12)
        if global_kw:
            st.subheader("🧠 Otomatik Kavram Yoğunluğu (Ön Tema Analizi)")
            kw_df = pd.DataFrame(list(global_kw.items()), columns=["Kavram", "Frekans"]).set_index("Kavram")
            st.bar_chart(kw_df, color="#2563EB")

        tab1, tab2 = st.tabs(["📄 Video & Transkript Veri Seti (MAXQDA)", "💬 İzleyici Yorumları Veri Seti"])
        with tab1:
            st.dataframe(df, use_container_width=True)
        with tab2:
            if not df_comments.empty:
                st.dataframe(df_comments, use_container_width=True)
            else:
                st.info("Bu videolar için yorum bulunamadı veya yorum çekme seçeneği kapalı.")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='1_Video_Transkriptler')
            if not df_comments.empty:
                df_comments.to_excel(writer, index=False, sheet_name='2_Izleyici_Yorumlari')
        
        st.download_button(
            label="📥 Çok Sekmeli MAXQDA & SPSS Veri Setini İndir (.xlsx)",
            data=output.getvalue(),
            file_name="akademik_arastirma_veri_seti_v2.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
