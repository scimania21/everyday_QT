import requests
from bs4 import BeautifulSoup
from google import genai
import datetime
import ftplib
import os

# ================= 필수 설정 =================
# 깃허브 Secrets(금고)에서 안전하게 가져오는 정보들입니다!
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FTP_HOST = os.environ.get("FTP_HOST")
FTP_USER = os.environ.get("FTP_USER")
FTP_PASS = os.environ.get("FTP_PASS")

TEMPLATE_FILE = "template.html" 
OUTPUT_FILE = "index.html"      

# 닷홈 FTP 폴더 경로 (성인부 전용 폴더입니다. 닷홈에 이 폴더가 꼭 있어야 합니다!)
FTP_DIR = "/html/adult_QT" 
# ========================================

def get_today_qt():
    # 매일성경(성인) 사이트 주소
    url = "https://sum.su.or.kr:8888/bible/today"
    
    # 봇 차단을 막기 위해 일반 브라우저인 것처럼 헤더 추가
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    response.encoding = 'utf-8' 
    soup = BeautifulSoup(response.text, 'html.parser')

    # 1. 제목 추출
    title_tag = soup.find('div', id='bible_text')
    title = title_tag.text.strip() if title_tag else "오늘의 말씀"

    # 2. 본문 구절 및 찬송 추출
    verse_tag = soup.find('div', id='bibleinfo_box')
    verse_ref = verse_tag.text.strip() if verse_tag else ""

    # 3. 성경 본문 추출
    bible_lines = []        # AI에게 줄 순수 텍스트용
    bible_html_lines = []   # 예쁜 웹사이트 화면용
    
    body_list = soup.find('ul', id='body_list')
    if body_list:
        for li in body_list.find_all('li'):
            num_div = li.find('div', class_='num')
            info_div = li.find('div', class_='info')
            
            if num_div and info_div:
                num = num_div.text.strip()
                text = info_div.text.strip()
                bible_lines.append(f"{num} {text}")
                bible_html_lines.append(f'<div class="verse"><div class="verse-num">{num}</div><div class="verse-text">{text}</div></div>')
            elif info_div:
                # 절 번호가 없는 소제목 등의 경우
                text = info_div.text.strip()
                bible_lines.append(text)
                bible_html_lines.append(f'<div class="verse"><div class="verse-text">{text}</div></div>')
                
    bible_text = "".join(bible_html_lines)
    bible_plain_text = "\n".join(bible_lines)
    
    return title, verse_ref, bible_text, bible_plain_text

def generate_contents(title, verse_ref, bible_plain_text):
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    당신은 성인 성도들을 영적으로 양육하고 위로하는 따뜻하고 지혜로운 목회자입니다.
    아래 성경 본문을 토대로 성인들이 깊이 공감하고 삶에 적용할 수 있는 묵상 내용을 만들어주세요.

    [작성 가이드라인]
    1. 대상: 직장, 가정, 사회에서 치열한 일상을 살아가는 모든 성인 성도.
    2. 어투: 정중하고 따뜻한 '해요체' 또는 '합쇼체(존댓말)'를 사용해주세요.
    3. 해설 깊이: 본문의 역사적/문맥적 배경을 짚어주어 성인 수준에 맞는 깊이 있는 신학적 통찰을 제공해주세요. (최소 6문장 이상)
    4. 적용과 기도: 직장 생활, 가정(부부 관계, 자녀 양육), 재정 문제, 인간관계, 질병, 교회 공동체 섬김 등 성인들이 겪는 현실적이고 보편적인 고민들을 깊이 있게 터치해주세요.

    본문 제목: {title}
    본문 구절: {verse_ref}
    성경 본문:
    {bible_plain_text}

    응답은 아래 형식만 엄격히 지켜주세요:
    [해설시작]
    (본문의 배경과 상황을 포함한 상세한 해설을 HTML 태그 없이 줄바꿈만 사용해 작성)
    [해설끝]
    [적용시작]
    <ul><li>실천사항 1</li><li>실천사항 2</li><li>실천사항 3</li></ul>
    [적용끝]
    [기도시작]
    (성도들의 삶을 위로하고 결단으로 이끄는 진심 어린 기도문)
    [기도끝]
    """
    
    try:
        # ✨ AI 모델을 가장 똑똑한 최신 버전인 gemini-2.5-flash로 세팅했습니다!
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        text = response.text
        
        commentary = text.split('[해설시작]')[1].split('[해설끝]')[0].strip()
        application = text.split('[적용시작]')[1].split('[적용끝]')[0].strip()
        prayer = text.split('[기도시작]')[1].split('[기도끝]')[0].strip()
        
        return commentary, application, prayer
        
    except Exception as e:
        print(f"⚠️ AI 생성 중 오류 발생: {e}")
        return "AI 목회자가 잠시 쉬고 있습니다. 오늘 주신 본문을 천천히 묵상하며 주님의 음성을 들어보시길 바랍니다.", "<ul><li>오늘 본문에서 나에게 주시는 하나님의 마음 묵상하기</li></ul>", "사랑의 주님, 오늘도 우리 성도들의 일터와 가정을 지켜주시고, 말씀 안에서 평안을 누리게 하옵소서. 예수님의 이름으로 기도드립니다. 아멘."

def create_html(title, verse_ref, bible_text, commentary, application, prayer):
    today = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        html = f.read()
        
    html = html.replace("{{DATE}}", today)
    html = html.replace("{{TITLE}}", title)
    html = html.replace("{{VERSE_REF}}", verse_ref)
    html = html.replace("{{BIBLE_TEXT}}", bible_text)
    html = html.replace("{{COMMENTARY}}", commentary)
    html = html.replace("{{APPLICATION}}", application)
    html = html.replace("{{PRAYER}}", prayer)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

def upload_to_ftp():
    try:
        print("🌐 FTP 서버에 접속합니다...")
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(FTP_DIR)
        
        print("📤 index.html 파일을 업로드하는 중...")
        with open(OUTPUT_FILE, 'rb') as f:
            ftp.storbinary(f'STOR {OUTPUT_FILE}', f)
        
        ftp.quit()
        print("✅ FTP 업로드 완료! 성인부 QT 사이트가 성공적으로 갱신되었습니다.")
    except Exception as e:
        print(f"❌ FTP 업로드 실패: {e}")

if __name__ == "__main__":
    try:
        print("1️⃣ 매일성경 오늘의 QT 데이터 가져오는 중...")
        t_title, t_ref, t_html_text, t_plain_text = get_today_qt()
        
        print("2️⃣ Gemini AI로 성인부 맞춤 해설 생성 중...")
        ai_commentary, ai_application, ai_prayer = generate_contents(t_title, t_ref, t_plain_text)
        
        print("3️⃣ HTML 파일 만드는 중...")
        create_html(t_title, t_ref, t_html_text, ai_commentary, ai_application, ai_prayer)
        
        print("4️⃣ 닷홈 서버로 전송 중...")
        upload_to_ftp()
        
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
