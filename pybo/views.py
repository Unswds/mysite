import os
import io
import re
import requests
from pathlib import Path
from django.conf import settings
from django.shortcuts import render
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import DailyUsage
from django.contrib import messages
import openai
from google.cloud.vision_v1 import types as vision_types

from django.conf import settings

# ─── 환경 설정 ─────────────────────────────────────────────
gpt_client    = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

# google vision은 settings 에서 만든 creds 를 직접 주입
# google vision은 settings 에서 만든 creds 를 직접 주입
from google.cloud import vision_v1
from django.conf import settings

vision_client = vision_v1.ImageAnnotatorClient(
    credentials=settings.VISION_CREDENTIALS,
    transport="rest",
)

# ─── 뷰 정의 ────────────────────────────────────────────────────────────
def main(request):
    """메인 페이지: 업로드 폼만 보여줌."""
    return render(request, 'pybo/main.html')


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required(login_url='common:login')
def photo_analysis(request):
    """GET: 폼 + (옵션) 방금 만든 이미지 보여주기"""
    today = timezone.localdate()
    usage, _ = DailyUsage.objects.get_or_create(user=request.user, date=today)
    remaining = max(20 - usage.count, 0)

    images = request.session.pop('generated_images', None)
    return render(request, 'pybo/photo_analysis.html', {
        'remaining': remaining,
        'images':    images,
    })

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.core.files.storage import default_storage
from django.conf import settings
import os

from .models import DailyUsage

# views.py  ── generate_scenes 뷰 (장르 선택 기능 통합版)
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from django.core.files.storage import default_storage
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
import os

# 이미 존재한다고 가정하는 유틸/모델
from .models import DailyUsage


@csrf_exempt
@login_required(login_url='common:login')
def generate_scenes(request):
    """
    이미지 업로드 → OCR → GPT 프롬프트 → (추가 요청사항 + 장르 스타일) 반영 → DALL·E 이미지 생성
    결과 리스트를 세션에 담아 photo_analysis로 리다이렉트
    """
    if request.method == "POST":
        # ── 0) 하루 사용량 제한 검사
        today = timezone.localdate()
        usage, _ = DailyUsage.objects.get_or_create(user=request.user, date=today)
        if usage.count >= 20:
            messages.error(request, '오늘 이미지·텍스트 분석 사용 횟수를 모두 소진했습니다. 내일 다시 이용해주세요.')
            return redirect('pybo:photo_analysis')

        # ── 1) 업로드된 이미지·폼 데이터 읽기
        uploaded_image = request.FILES.get("image")
        instructions   = request.POST.get("instructions", "").strip()
        genre          = request.POST.get("genre", "").strip()       # ⭐ 장르

        # ── 2) OCR 수행 (이미지 있을 때만)
        if uploaded_image:
            saved_path = default_storage.save(f'temp/{uploaded_image.name}', uploaded_image)
            full_path  = os.path.join(settings.MEDIA_ROOT, saved_path)
            ocr_text   = extract_text(full_path)
        else:
            ocr_text = ""

        # ── 3) 텍스트 합치기
        if ocr_text and instructions:
            combined_text = f"{ocr_text}\n\n추가 요청사항:\n{instructions}"
        elif ocr_text:
            combined_text = ocr_text
        else:
            combined_text = instructions

        # ── 4) GPT로부터 원본 프롬프트 생성
        raw_prompts = generate_prompts(combined_text, instructions)

        # ── 5) 장르별 스타일 문구 결정
        STYLE_MAP = {
            "로맨스": "부드러운 파스텔 톤 로맨스 삽화 스타일로 그려주세요.",
            "판타지": "화려한 판타지 소설 삽화 스타일로 그려주세요.",
            "SF":     "미래적인 SF 삽화 느낌으로 그려주세요.",
            "추리":   "필름 누아르 분위기의 추리 삽화처럼 그려주세요.",
            "공포":   "어두운 고딕 호러 삽화 스타일로 그려주세요.",
        }
        default_style = "웹툰 스타일로 그려주세요."
        style_tail = STYLE_MAP.get(genre, default_style)
        import logging
        logger = logging.getLogger(__name__)
        # ── 6) 스타일 태그 추가 + 길이 제한
        styled_prompts = []
        for p in raw_prompts:
            base = f"{instructions}. {p}" if instructions else p
            if len(base) > 250:
                base = base[:250] + "…"
            styled_prompts.append(f"{base}, {style_tail}")
        logger.debug("▶ 최종 프롬프트: %s", styled_prompts) 

        # ── 7) DALL·E 이미지 생성
        generated = generate_images(styled_prompts)
        if not generated:
            messages.error(request, '이미지 생성 중 오류가 발생했습니다. 다시 시도해주세요.')
            return redirect('pybo:photo_analysis')

        # ── 8) raw_prompts와 URL 매핑
        images = [
            (raw_prompts[i], generated[i][1])
            for i in range(min(len(raw_prompts), len(generated)))
        ]

        # ── 9) 사용량 1회 차감
        usage.increment()

        # ── 10) 세션에 결과 저장 후 리다이렉트
        request.session['generated_images'] = images
        return redirect('pybo:photo_analysis')

    # GET인 경우엔 무조건 photo_analysis로
    return redirect('pybo:photo_analysis')

# ─── 헬퍼 함수 ──────────────────────────────────────────────────────────
def load_base_info(path="base_info_robot.txt"):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def extract_text(image_path):
    """이미지에서 텍스트 추출 (OCR)"""
    with io.open(image_path, 'rb') as img_f:
        content = img_f.read()
    image = vision_types.Image(content=content)
    resp = vision_client.text_detection(image=image)
    texts = resp.text_annotations
    return texts[0].description if texts else ""


def generate_prompts(text, instructions="", base_info_path="base_info_robot.txt"):
    """GPT로부터 시각 장면 프롬프트를 한국어로 생성"""
    base_info = load_base_info(base_info_path)
    prompt = f'''
당신은 시각 장면 분해 어시스턴트입니다.

기본 정보:
"""{base_info}"""

    ### 공통 설정
    {instructions or "없음"}

다음 텍스트를 읽고, 시각적으로 중요한 1~2개의 장면을 한국어로 간결하게 설명하는 프롬프트를 작성하세요.

텍스트:
"""{text}"""
'''
    resp = gpt_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=1200
    )
    content = resp.choices[0].message.content
    # "1. 장면 A\n2. 장면 B" 형태로 넘어오기 때문에, 정규 표현식으로 뽑아낸다.
    return re.findall(r"\d+\.\s*(.+)", content)


def generate_images(prompts):
    """DALL·E를 통해 이미지 생성"""
    urls = []
    for p in prompts:
        try:
            resp = gpt_client.images.generate(
                model="dall-e-3",
                prompt=p,
                size="1024x1024",
                quality="standard",
                n=1
            )
            url = resp.data[0].url
            urls.append((p, url))
        except Exception as e:
            print("Generation error:", e)
    return urls

# pybo/views.py
from django.shortcuts import render
from django.db.models import Q
from .models import Book
@login_required(login_url='common:login')
def book_gallery(request):
    books = Book.objects.order_by('id')[:6]
    return render(request, "pybo/book_gallery.html", {"books": books})


from django.shortcuts import render
from .models import Book
@login_required(login_url='common:login')
def book_search(request):
    # ① static 커버 이미지 경로 리스트
    covers = [f'pybo/images/covers/cover{i}.jpg' for i in range(1, 7)]
    # ② 각 이미지에 대응할 캡션 리스트
    captions = [
        "27세기의 발명왕",    # cover1.jpg
        "도망친 로봇",        # cover2.jpg
        "심해의 우주괴물",        # cover3.jpg
        "이상한 존", # cover4.jpg
        "공룡 세계의 탐험", # cover5.jpg
        "백설의 공포"   # cover6.jpg
    ]
    # ③ path, caption 묶어서 리스트로 생성
    cover_items = [
        {"path": path, "caption": caption}
        for path, caption in zip(covers, captions)
    ]

    return render(request, 'site1/book_search.html', {
        'cover_items': cover_items,
    })

from django.contrib.staticfiles import finders
from django.http                import Http404
from django.shortcuts           import render
@login_required(login_url='common:login')
def book_detail(request, idx, page):
    # ➊ 책 전체 제목
    book_titles = {
        1: "27세기의 발명왕",
        2: "도망친 로봇",
        3: "심해의 우주괴물",
        4: "이상한 존",
        5: "공룡 세계의 탐험",
        6: "백설의 공포",
    }
    book_title = book_titles.get(idx, "알 수 없는 책")

    # ➋ 페이지별 “강조 제목” / “부제목(caption)” / “설명(description)” 리스트
    page_headings = {
        1: ["배경", "알프스의 첫 만남", "빛의 탑 투어", "투명화 납치 구출", "약혼과 최면 납치", "우주선 추격전","부활의 기적"],
        2: ["배경", "가니메데에서의 작별과 렉스 판매 결정", "비인간적 농장 생활과 절체절명의 탈출", "사막 횡단과 동굴 속 극적 재회", "화물선 ‘드라베라호’ 밀항 작전", "에필로그"],
        3: ["배경", "이상 현상의 목격", "심해 조사와 외계 생물의 정체", "‘바다의 전차’ 전투", "지구 기후 위기와 대홍수", "반격과 새로운 세계"],
        4: ["배경", "등장과 비범한 성장", "초인적 능력의 발견과 실험", "같은 무리(에스퍼) 탐색과 만남", "에스퍼 섬(新천지) 건설 계획", "외부 세계와 첫 충돌","최후의 날과 종말"],
        5: ["배경", "탐험대 결성", "아마존 진입", "공룡과의 교전", "배신과 증거 확보", "비행 풍선 탈출","잃어버린 세계 입증"],
        6: ["배경", "이상 기후의 단서 탐색", "스스로 움직이는 눈의 탄생", "생명체를 말려 버리는 공포", "카렌의 위기와 눈의 아메바化", "다이아몬드 안개와 치명적 핵","소금과 뜨거운 물의 최후 대결 & 메시지"],
    }
    page_captions = {
    }
    page_descriptions = {
        1: [
            "2660년대, 세계 정부가 통치하는 27세기. 전쟁은 사라지고 과학 기술이 비약적으로 발전해 반중력 비행차·입체 TV·무중력 서커스·공중 도시 등이 일상화된 시대다. 주인공은 인류 최고 발명가이자 ‘플러스(+)’ 훈장을 받은 뉴욕의 과학자 랄프 124C41⁺. 그는 죽은 생물을 부활시키는 신기술까지 개발해 세계의 존경을 받고 있다.",
            "텔레비전 전화 혼선으로 랄프는 스위스 알프스 산중에 고립된 소녀 아리스 212B423를 우연히 화면에서 만난다. 아리스가 눈사태에 위협받자 랄프는 고출력 전파열로 눈더미를 증발시켜 그녀를 구한다.",
            "아리스와 아버지 제임스는 뉴욕의 ‘빛의 탑’에 머물며 랄프의 안내로 첨단 도시, 태양 발전소, 무중력 서커스 등을 견학한다. 하지만 아리스를 집요하게 따라다니는 프랑스 과학자 페르난 600D10와, 거대한 녹색 피부의 화성인 유학생 리자놀 AK42가 두 사람을 질투어린 눈빛으로 지켜본다.",
            "고속도로 산책 중 아리스가 sp급 고주파(물체를 투명화하는 전파)에 의해 눈앞에서 사라진다. 랄프는 직접 제작한 탐지기로 전파원을 찾아내 양복점 뒤에 숨겨진 범인의 아지트를 급습, 투명 상태로 묶여 있던 아리스를 구출한다. 범인은 페르난이었음이 드러난다.",
            "랄프와 아리스가 약혼을 발표하자 전 세계가 환호한다. 그러나 페르난은 화성인 리자놀과 손을 잡고 재차 납치를 꾀한다. 달빛 드라이브 중 가짜 조난 신호를 보내 랄프에게 최면 가스를 살포하고, 정신을 잃은 그 사이 아리스를 데려가 화성행 우주선에 승선한다. ",
            "랄프는 전용선 카시오페이아호로 뒤쫓는다. 레이더로 리자놀의 함선을 포착해 광선총과 ‘빛 중화 장치’(빛과 같은 주파수의 전파로 공간을 암흑화)로 교란, 적선을 제압한다. 적선에는 페르난만 기절한 채 남아 있고, 리자놀은 아리스를 데리고 도주한 뒤였다. ",
            "끝내 리자놀의 선박을 격파하지만, 랄프가 들어갔을 때 리자놀은 이미 사망했고 아리스는 가슴에 단검이 박힌 채 피투성이로 쓰러져 있다. 아리스는 숨을 거두고, 절망한 랄프는 시신을 지구로 가져와 자신의 ‘부활 장치’로 연명 실험을 실시한다. 처음엔 실패했으나, 동료의 외침과 함께 아리스의 심장이 다시 뛰기 시작한다. 인류 최초의 인간 부활이 성공한 순간이다. ",
        ],
        2: [
            "목성의 위성 가니메데 돔 도시 산발레이에서, 희박한 대기로 기압복 없이는 생존이 불가능하다. 16세 소년 폴과 그의 가정용 로봇 렉스(Q=5=7=356)는 곧 지구로 돌아갈 계획이었으나, 운송비 절감을 위해 폴의 아버지는 렉스를 농장주에게 팔아넘긴다. 사랑하는 친구를 잃은 폴과 로봇의 절박한 탈출 여정이 시작된다.",
            "폴의 가족은 10일 뒤 지구로 귀환한다는 기쁜 소식을 듣지만, 우주 운송비 부담으로 아버지는 가정용 로봇 렉스(Q=5=7=356)를 농장주에게 팔기로 결정한다.",
            "농장에서 억압적 노동에 내몰리며 파괴 위기에 처한 렉스는 직접 농장을 탈출해 사막을 횡단, 4시간을 달려 공항으로 향한다.",
            "폴은 스타퀸호를 무단 탑승해 사막의 비상용 동굴에 숨어든 뒤, 우연히 렉스와 재회해 이후 탈출 계획을 세운다.",
            "렉스는 화물칸 로봇으로 위장해 드라베라호에 잠입하여 선장의 신임을 얻고, 수리·청소·식사 준비 등 다양한 임무를 수행하며 성공적으로 밀항에 성공한다. ",
            "화성이 가까워지며 수색대의 추격을 받지만, 렉스는 수소광선총을 무력화해 폴을 구출한다. 두 사람은 지구로 무사 귀환해 렉스는 영웅으로 인정받으며 폴과 진정한 재회를 이룬다."
        ],
        3: [
            "1950년대 중반, 7월 15일 밤 대서양 한가운데에서 이야기가 시작된다. ‘실크베일 호’는 아조레스 섬을 향해 항해 중이며, 검은 파도가 물결치는 바다 위로 별빛이 반사되어 은은히 빛난다. ",
            "영국의 방송 기자 마이크 왓슨은 아내 필리스와 함께 대서양을 항해하던 중 밤바다 위로 다섯 개의 붉은 ‘불덩이’가 떨어지는 것을 목격한다. 이들은 단순한 유성이 아니라, 해저로 투하된 외계 물체였음이 곧 밝혀진다.",
            "미 해군은 특수 잠수구로 심해를 탐사하려 하나, 괴이한 생명체가 파이프를 녹여 잠수구를 끊어버린 뒤 실종된다. 이어 투하된 원자폭탄 두 기가 돌연 행방불명되자, 지질학자 보커 박사는 “이들은 목성에서 왔을 것”이라 추정하며 외계 기원의 가능성을 제기한다.",
            "인류는 심해 생물과 직접 교전을 벌이기 위해 수중 전차(해저 장갑차)를 개발·투입한다. 이를 통해 최초의 심해 전투가 벌어지고, ‘바다의 전차’라는 별칭으로 불리게 된 이 전투는 곧 해양 전쟁 양상을 띠게 된다.",
            "외계 생물의 활동으로 해양 온도가 상승하고, 극지방의 얼음이 녹아 대홍수가 발생한다. 북극의 얼음이 무너지며 전 지구적 해수면 상승과 이상 기후 현상이 속출하고, 인류는 생존을 위한 절박한 대응에 나선다",
            "과학자들은 외계 생물이 고온에 강하나 극저온에 약하다는 사실을 발견하고, 인위적인 냉각 작전을 통해 심해 괴물을 무력화시킨다. 이어 재편된 해양 환경 속에서 인류는 ‘새로운 세계’를 맞이하며, 한층 성숙해진 과학적·사회적 균형을 이루는 결말을 맞는다",
        ],
        4: [
            "소설은 초인(에스퍼)의 등장을 통해 미래 사회가 근본적으로 변모하는 가운데, 인류학자 화자가 비범한 지능과 초능력을 지닌 소년 ‘이상한 존’을 기록하는 이야기다. 존은 같은 에스퍼들을 모아 남미의 외딴섬에 비밀 공동체를 세우지만, 강대국들의 군사적 봉쇄 속에서 비극적 파국을 맞이한다.",
            "화자는 ‘이상한 존’의 전기를 쓰기로 결심하면서 이야기가 시작된다. 존은 태어날 때부터 신체 발달이 느리지만, 1~2세 무렵부터 지능이 비상하게 발현되어 언어와 수 개념을 금세 습득한다. 4세에는 문법적으로 완전한 문장을 구사하고, 5세에는 12진법과 10진법의 불일치를 지적하며 “인간은 모두 바보”라고 단언한다.",
            "존은 기하학·물리학·언어학을 섭렵하고 텔레파시·최면술·시간 지각 왜곡 같은 정신적 능력을 차례로 깨닫는다. 스코틀랜드 산속 동굴에서 생존 실험을 하며 자신의 신체·정신 한계를 스스로 시험한다. 우연히 만난 등산가 둘을 통해 텔레파시로 상대의 기억을 지우는 능력까지 입증한다.",
            "존은 자신과 유사한 초인(에스퍼)을 찾기 위해 유럽·아프리카·아시아를 여행하며, 파리에서 여성 에스퍼 ‘재크리느’를 만나고 티베트인·프랑스인·이집트인 등 여러 에스퍼를 확인한다.",
            "존과 에스퍼들은 남미 연안 외딴 섬에 비밀 식민지를 건설해, 선박·비행기·발전소·도서관·실험실을 갖춘 도시를 섬 안에 숨긴 채 문명과 다른 삶을 영위한다.",
            "섬의 존재가 소련 탐험대와 언론을 통해 알려지자 6개국 연합 함대가 출동한다. 대표자들을 초청해 설득을 시도하지만, 독일 대표가 체포를 명령하자 즉시 사망자가 발생하고 에스퍼들은 최면·정신력·물리력 등 모든 수단으로 자신을 보호한다.",
            "6개국 연합은 섬을 완전 봉쇄하고 주민에게 5시간 내 퇴거를 명령한다. 존은 최후 항전을 결의하고 모두 함께 석조 건물 안으로 들어가 폭발을 일으켜 섬을 가라앉힌다. 이 사건으로 이상한 존과 그의 무리는 역사 속으로 사라진다.",
        ],
        5: [
            "1900년대 초, 영국 런던의 젊은 기자 에드워드 머론은 괴짜 과학자 챌린저 교수가 남아메리카 아마존 오지에서 살아 있는 공룡을 목격했다는 충격적 폭로를 듣고 진실을 확인하기 위해 나선다. 머론은 비교해부학자 사마리 박사, 모험가 록스턴 경 등과 함께 ‘잃어버린 세계’라 불리는 미지의 고원으로 향해, 고대 생명체가 여전히 생존한다는 전설을 쫓는다",
            "에드워드 머론 기자는 챌린저 교수가 아마존 오지에서 살아 있는 공룡을 목격했다는 폭로를 듣고 직접 인터뷰를 청해, 비교 해부학자 사마리 박사 및 모험가 록스턴 경과 함께 ‘잃어버린 세계’ 탐험대를 결성한다 .",
            "원정대는 파라를 거쳐 증기선과 통나무배로 아마존 강을 거슬러 올라가지만, 챌린저 교수의 봉투에는 빈 종이 한 장뿐이었으나 그 지도로 진짜 서식처를 찾아 나선다. 여정 중 거대한 공룡 발자국과 테라노돈의 비행 흔적 등을 차례로 목격한다.",
            "깊은 정글 야영 중 인디언들이 티라노사우루스에게 사냥당하는 참혹한 장면을 목격하고, 이후 여러 차례 공룡과의 교전에서 사마리 박사가 중상을 입지만 록스턴 경의 사격과 챌린저 교수의 결단으로 간신히 위기를 넘긴다.",
            "고용원 고메즈의 배신으로 절벽 아래로 떨어질 위기에 처하지만, 머론과 록스턴은 식물·곤충 표본 및 다이아몬드 샘플 등 과학적 증거를 확보하는 데 성공한다.",
            "정글 곳곳의 자연 동굴을 따라 탈출구를 발견한 뒤 챌린저 교수의 비행 풍선 ‘하늘을 나는 경기구’를 타고 고원을 벗어나 문명 세계로 귀환한다 ",
            "런던으로 돌아온 원정대는 살아 있는 공룡 화석과 수집한 표본, 다이아몬드를 학계와 언론에 공개하여 ‘잃어버린 세계’의 존재를 확증하고 명성을 얻는다",
        ],
        6: [
            "이 소설은 물 부족이 심각해진 가을 초, 미국 뉴햄프셔의 작은 마을 웨스트오버와 인근 케인필드에서 국지적인 눈보라가 몰아치는 이상 기후를 배경으로 한다. 풋내기 기자 데이비드가 화학자 네이슨 교수의 인공우 실험 현장을 찾아가며, 실험실에서 탄생한 ‘쌍결정 눈’ 괴물의 비밀이 드러난다.",
            "기자 데이비드는 국지적 눈보라가 몰아치는 케인필드를 취재하던 중, 눈이 내리지 않은 지역에서 거대한 눈 덩어리가 자라나는 기이한 현장을 목격하고 원인을 조사하기 위해 화학자 네이슨 교수에게 접근한다.",
            "인공 실험으로 만들어진 눈 결정이 쌍결정으로 성장하며 자가 팽창하고, 눈사람이나 눈의 벽처럼 바람 방향과 반대로 이동하며 주변의 수분을 모두 빨아들이는 ‘살아 있는 눈’의 정체가 서서히 드러난다.",
            "눈 괴물이 지나간 자리에서는 들쥐·가축·야생동물이 모두 탈수된 뼈 상태로 발견되며, 흔적 없이 생명체를 ‘흡수’하는 잔혹함이 확인된다.",
            "네이슨 교수의 딸 카렌이 눈 괴물에게 납치되고, 데이비드 일행은 유체처럼 변형된 눈 속에서 그녀를 구출하기 위해 필사적인 탈출을 감행한다.",
            "눈 괴물과 함께 다가오는, 다이아몬드처럼 반짝이는 미세한 안개가 또 다른 핵심 위협으로 부상하며, 소금만으로는 결정 구조를 완전히 파괴하기 어려운 새로운 난관이 등장한다.",
            "팀은 암염과 고압 호스를 동원해 눈 결정과 안개의 핵을 분리·용해시켜 괴물을 소탕하는 데 성공하고, 작가는 이를 통해 ‘통제되지 않은 과학’의 위험성과 책임을 경고한다. ",
        ],
    }
    headings     = page_headings.get(idx, [])
    captions     = page_captions.get(idx, [])
    descriptions = page_descriptions.get(idx, [])

    # ➌ 이미지 로드
    pages = []
    # 1p1.jpg
    rel = f'pybo/images/books/{idx}p1.jpg'
    if not finders.find(rel):
        raise Http404("책을 찾을 수 없습니다.")
    pages.append({'path': rel})
    # p2~ .png
    pno = 2
    while True:
        rel = f'pybo/images/books/{idx}p{pno}.png'
        if not finders.find(rel):
            break
        pages.append({'path': rel})
        pno += 1

    # ➍ 키 값 매핑
    for i, pg in enumerate(pages):
        pg['heading']     = headings[i]     if i < len(headings)     else f"페이지 {i+1}"
        pg['caption']     = captions[i]     if i < len(captions)     else ""
        pg['description'] = descriptions[i] if i < len(descriptions) else ""

    # ➎ 페이징 계산
    total     = len(pages)
    prev_page = page-1 if page>1     else None
    next_page = page+1 if page<total else None
    current   = pages[page-1]

    return render(request, 'site1/book_detail.html', {
        'book_title': book_title,
        'idx':        idx,
        'page':       page,
        'pages':      pages,
        'prev_page':  prev_page,
        'next_page':  next_page,
        'total':      total,
        'current':    current,
    })
# ── imports ───────────────────────────────────────────
# pybo/views.py  ──────────────────────────────────────────────
import os, io, re
from pathlib import Path
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse      # ← AJAX용

import openai
from django.conf import settings

gpt_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages

from .models import DailyUsage

# pybo/views.py

from django.shortcuts      import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf   import csrf_exempt
from django.utils          import timezone
from django.http           import JsonResponse
from django.contrib        import messages

from .models import DailyUsage

# ── ① 페이지 렌더링 전용 (GET만 처리)
@csrf_exempt                      # JS fetch 를 쓸 때 편리
@login_required(login_url='common:login')
def text_analysis(request):
    """
    GET: 텍스트 분석 페이지 렌더링 (남은 횟수만 전달)
    """
    today, usage = timezone.localdate(), None
    usage, _ = DailyUsage.objects.get_or_create(user=request.user, date=today)
    remaining = max(20 - usage.count, 0)

    return render(request, 'site1/text_analysis.html', {
        'remaining': remaining,
    })


# ── ② AJAX 전용: 분석 요청(POST) → JSON 반환
@csrf_exempt
@login_required(login_url='common:login')
def analyze_text(request):
    """
    POST: { message } 를 받아 GPT로 분석 → JSON으로 { analysis, remaining } 반환
    """
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid method'}, status=405)

    today, usage = timezone.localdate(), None
    usage, _ = DailyUsage.objects.get_or_create(user=request.user, date=today)
    if usage.count >= 20:
        return JsonResponse({'error': '오늘 분석 가능 횟수를 모두 소진했습니다.'}, status=403)

    user_text = request.POST.get("message", "").strip()
    if not user_text:
        return JsonResponse({'error': '분석할 텍스트를 입력해주세요.'}, status=400)

    # GPT 호출
    prompt = f"""
    당신은 한국어 전문 텍스트 분석 어시스턴트입니다.
    사용자가 입력한 글을 핵심 주제 3-5가지로 묶어 간결하게 요약하고,
    각 주제별로 간략한 인사이트나 개선 포인트가 있으면 함께 제시하세요.

    원문:
    \"\"\"{user_text}\"\"\"
    """
    resp = gpt_client.chat.completions.create(
        model       = "gpt-4o-mini",
        messages    = [{"role":"user","content":prompt}],
        temperature = 0.4,
        max_tokens  = 800,
    )
    analysis = resp.choices[0].message.content.strip()

    # 사용량 차감
    usage.increment()
    remaining = max(20 - usage.count, 0)

    return JsonResponse({
        'analysis': analysis,
        'remaining': remaining
    })



# pybo/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@csrf_exempt
@login_required(login_url='common:login')
@require_POST
def analyze_text(request):
    # ── 호출 제한 검사
    today = timezone.localdate()
    usage, _ = DailyUsage.objects.get_or_create(user=request.user, date=today)
    if usage.count >= 20:
        return JsonResponse({"error": "오늘 이미지·텍스트 분석 사용 횟수를 모두 소진했습니다."}, status=403)

    message = request.POST.get("message", "").strip()
    if not message:
        return JsonResponse({"error": "message 필드가 비어 있습니다."}, status=400)

    # 1) (예시) 입력 문장을 그대로 프롬프트로 삼거나 필요한 전처리 수행
    prompts = [f"{message}, 웹툰 스타일로 그려주세요."]  # ① 수정: 웹툰풍으로

    # 2) 기존 헬퍼 재사용해서 이미지 생성
    images = generate_images(prompts)   # [(prompt, url), …] or []

    if not images:
        return JsonResponse({"error": "이미지 생성 실패"}, status=500)

 
    # ── 성공 호출 기록
    usage.increment()

    prompt, url = images[0]
    return JsonResponse({"prompt": prompt, "url": url})
